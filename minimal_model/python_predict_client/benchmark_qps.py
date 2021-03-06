#!/usr/bin/env python

import numpy
import multiprocessing
import threading
import time

from grpc.beta import implementations
import tensorflow as tf

import predict_pb2
import prediction_service_pb2

tf.app.flags.DEFINE_string("host", "127.0.0.1", "gRPC server host")
tf.app.flags.DEFINE_integer("port", 9000, "gRPC server port")
tf.app.flags.DEFINE_string("model_name", "cancer", "TensorFlow model name")
tf.app.flags.DEFINE_integer("model_version", 1, "TensorFlow model version")
tf.app.flags.DEFINE_float("request_timeout", 100.0, "Timeout of gRPC request")
tf.app.flags.DEFINE_integer("benchmark_batch_size", 1, "")
tf.app.flags.DEFINE_integer("benchmark_test_number", 10000, "")
tf.app.flags.DEFINE_integer("benchmark_thread_number", 10, "")
FLAGS = tf.app.flags.FLAGS


def _create_rpc_callback(event):
  def _callback(result_future):
    event.set()
    exception = result_future.exception()
    if exception:
      print(exception)
    else:
      pass
      #print("No exception after callback")

  return _callback


def test_one_process(i):
  host = FLAGS.host
  port = FLAGS.port
  model_name = FLAGS.model_name
  model_version = FLAGS.model_version
  request_timeout = FLAGS.request_timeout

  request_batch = FLAGS.benchmark_batch_size
  request_data = [i for i in range(request_batch)]
  # Generate inference data
  features = numpy.asarray(request_data)
  features_tensor_proto = tf.contrib.util.make_tensor_proto(features,
                                                            dtype=tf.float32)

  # Create gRPC client and request
  channel = implementations.insecure_channel(host, port)
  stub = prediction_service_pb2.beta_create_PredictionService_stub(channel)
  request = predict_pb2.PredictRequest()
  request.model_spec.name = model_name
  request.model_spec.version.value = model_version
  request.inputs['features'].CopyFrom(features_tensor_proto)

  # Send request
  request_number = FLAGS.benchmark_test_number
  #start_time = time.time()

  events = []
  for i in range(request_number):
    event = threading.Event()
    result_future = stub.Predict.future(request, request_timeout)
    #result_future = stub.Predict.future(request, 0.00000001)
    result_future.add_done_callback(_create_rpc_callback(event))
    events.append(event)
    #result = stub.Predict(request, request_timeout)

    #end_time = time.time()
    #print("Average latency is: {} ms".format((end_time - start_time) * 1000 / request_number))
    #print("Average qps is: {}".format(request_number / (end_time - start_time)))

  for event in events:
    event.wait()


def main():
  thread_number = FLAGS.benchmark_thread_number

  p = multiprocessing.Pool(thread_number)

  start_time = time.time()

  for i in range(thread_number):
    p.apply_async(test_one_process, args=(i, ))

  p.close()
  p.join()

  end_time = time.time()
  request_number = FLAGS.benchmark_test_number * thread_number
  print("Average qps is: {}".format(request_number / (end_time - start_time)))


if __name__ == '__main__':
  main()

import argparse
import gzip
import os
import shutil
import tempfile
import urllib.request

import numpy as np
import tensorflow as tf


def read32(bytestream):
    """Read 4 bytes from bytestream as an unsigned 32-bit integer."""
    dt = np.dtype(np.uint32).newbyteorder('>')
    return np.frombuffer(bytestream.read(4), dtype=dt)[0]


def check_image_file_header(filename):
    """Validate that filename corresponds to images for the MNIST dataset."""
    with tf.gfile.Open(filename, 'rb') as f:
        magic = read32(f)
        read32(f)  # num_images, unused
        rows = read32(f)
        cols = read32(f)
        if magic != 2051:
            raise ValueError(f'Invalid magic number {magic} in MNIST file {f.name}')
        if rows != 28 or cols != 28:
            raise ValueError(
                f'Invalid MNIST file {f.name}: Expected 28x28 images, found {rows}x{cols}')


def check_labels_file_header(filename):
    """Validate that filename corresponds to labels for the MNIST dataset."""
    with tf.gfile.Open(filename, 'rb') as f:
        magic = read32(f)
        read32(f)  # num_items, unused
        if magic != 2049:
            raise ValueError(f'Invalid magic number {magic} in MNIST file {f.name}')


def download(directory, filename):
    """Download (and unzip) a file from the MNIST dataset if not already done."""
    filepath = os.path.join(directory, filename)
    if tf.gfile.Exists(filepath):
        return filepath
    if not tf.gfile.Exists(directory):
        tf.gfile.MakeDirs(directory)

    url = f'http://yann.lecun.com/exdb/mnist/{filename}.gz'
    _, zipped_filepath = tempfile.mkstemp(suffix='.gz')
    print(f'Downloading {url} to {zipped_filepath}')
    urllib.request.urlretrieve(url, zipped_filepath)
    with gzip.open(zipped_filepath, 'rb') as f_in, \
            tf.gfile.Open(filepath, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
    os.remove(zipped_filepath)
    return filepath


def dataset(directory, images_file, labels_file):
    """Download and parse MNIST dataset."""

    images_file = download(directory, images_file)
    labels_file = download(directory, labels_file)

    check_image_file_header(images_file)
    check_labels_file_header(labels_file)

    def decode_image(image):
        # Normalize from [0, 255] to [0.0, 1.0]
        image = tf.decode_raw(image, tf.uint8)
        image = tf.cast(image, tf.float32)
        image = tf.reshape(image, [784])
        return image / 255.0

    def decode_label(label):
        label = tf.decode_raw(label, tf.uint8)  # tf.string -> [tf.uint8]
        label = tf.reshape(label, [])  # label is a scalar
        return tf.to_int32(label)

    images = tf.data.FixedLengthRecordDataset(
        images_file, 28 * 28, header_bytes=16).map(decode_image)
    labels = tf.data.FixedLengthRecordDataset(
        labels_file, 1, header_bytes=8).map(decode_label)
    return tf.data.Dataset.zip((images, labels))


def autoencoder_dataset(directory, images_file):
    """Download and parse MNIST dataset."""

    images_file = download(directory, images_file)

    check_image_file_header(images_file)
    check_labels_file_header(labels_file)

    def decode_image(image):
        # Normalize from [0, 255] to [0.0, 1.0]
        image = tf.decode_raw(image, tf.uint8)
        image = tf.cast(image, tf.float32)
        image = tf.reshape(image, [784])
        return image / 255.0

    def decode_label(label):
        label = tf.decode_raw(label, tf.uint8)  # tf.string -> [tf.uint8]
        label = tf.reshape(label, [])  # label is a scalar
        return tf.to_int32(label)

    images = tf.data.FixedLengthRecordDataset(
        images_file, 28 * 28, header_bytes=16).map(decode_image)
    labels = tf.data.FixedLengthRecordDataset(
        labels_file, 1, header_bytes=8).map(decode_label)
    return tf.data.Dataset.zip((images, labels))


def train_dataset(directory):
    """tf.data.Dataset object for MNIST training data."""
    return dataset(directory, 'train-images-idx3-ubyte',
                   'train-labels-idx1-ubyte')


def test_dataset(directory):
    """tf.data.Dataset object for MNIST test data."""
    return dataset(directory, 't10k-images-idx3-ubyte', 't10k-labels-idx1-ubyte')


def parse_args(args):
    convert_parser = argparse.ArgumentParser(
        description='Tool for preparing datasets in TFRecord format '
                    'from AOV data.')

    convert_parser.add_argument(
        '-id', '--input-dir',
        type=str,
        required=True,
        action='store',
        help='path to the directory containing input AOV data')

    convert_parser.add_argument(
        '-od', '--output-dir',
        type=str,
        required=True,
        action='store',
        help='path to the output TFRecord-file')

    convert_parser.add_argument(
        '-dn', '--dataset-name',
        type=str,
        required=False,
        action='store',
        help='[default: Basename of INPUT_DIR] Name of the result dataset')

    convert_parser.add_argument(
        '-tm', '--training-mode',
        required=False,
        action='store_true',
        help='Automatically divide data into training and evaluation parts')

    return convert_parser.parse_args(args)


def main(argv):
    build_dataset(parse_args(args=argv[1:]))


if __name__ == "__main__":
    main(argv=sys.argv)

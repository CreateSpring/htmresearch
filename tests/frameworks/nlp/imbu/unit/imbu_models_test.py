# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2016, Numenta, Inc.  Unless you have purchased from
# Numenta, Inc. a separate commercial license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------

import numpy
import os
import shutil
import tempfile
import unittest

from htmresearch.encoders import EncoderTypes
from htmresearch.frameworks.nlp.imbu import ImbuModels
from htmresearch.frameworks.nlp.classification_model import (
  ClassificationModel
)
from htmresearch.frameworks.nlp.classify_network_api import (
  ClassificationNetworkAPI
)



TEST_DATA_DIR = os.path.abspath(
  os.path.join(
    os.path.dirname(
      os.path.realpath(__file__)
    ),
    "..", "..", "nlp", "unit", "test_data"
  )
)



class TestImbu(unittest.TestCase):

  def setUp(self):
    self.dataPath = os.path.join(TEST_DATA_DIR, "sample_reviews_subset.csv")


  def tearDown(self):
    if os.path.exists("fake_cache_root"):
      shutil.rmtree("fake_cache_root")


  def _setupFakeImbuModelsInstance(self, retina="en_associative"):
    return ImbuModels(
      cacheRoot="fake_cache_root",
      dataPath=self.dataPath,
      retina=retina,
      apiKey=os.environ.get("CORTICAL_API_KEY")
    )


  def _createTempModelCheckpoint(self):
    tmpDir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, tmpDir)
    return os.path.join(tmpDir, "checkpoint")


  def testCreateModel(self):
    imbu = self._setupFakeImbuModelsInstance()

    # You must specify a known model type
    self.assertRaises(TypeError, imbu.createModel, "random model type")

    # Assert that you can create models of known types from scratch (i.e. with
    # empty loadPath value)
    for modelType in imbu.modelMappings:
      # You _must_ specify loadPath and savePath.  Assert that attempts to not
      # specify will result in failure
      self.assertRaises(TypeError, imbu.createModel, modelType)
      self.assertRaises(TypeError, imbu.createModel, modelType, None)
      self.assertRaises(ValueError, imbu.createModel, modelType, None, None)

      # Attempt to create model using default arguments
      model = imbu.createModel(
        modelType, "", "", networkConfigName="imbu_sensor_knn.json"
      )

      # Assert model created was one of the expected types
      self.assertTrue(isinstance(model, ClassificationModel) or
                      isinstance(model, ClassificationNetworkAPI))


  def _exerciseModelLifecycle(self, modelType, queryTerm="unicorn",
                              networkConfigName="imbu_sensor_knn.json",
                              retina="en_associative"):
    """ Create, save, load, and assert consistent results."""

    imbu = self._setupFakeImbuModelsInstance(retina=retina)

    checkpointLocation = self._createTempModelCheckpoint()

    # Create model with no load path.  This should trigger the creation of a
    # new intance, and train it.  Specify save path so that the trained model
    # gets saved
    originalModel = imbu.createModel(modelType,
                                     loadPath="",
                                     savePath=checkpointLocation,
                                     networkConfigName=networkConfigName)

    # Make a query, keep around for later comparison
    originalQueryResults = imbu.query(originalModel, queryTerm)

    del originalModel

    # Create model, specifying previous load path
    model = imbu.createModel(modelType,
                             loadPath=checkpointLocation,
                             savePath=checkpointLocation,
                             networkConfigName=networkConfigName)

    self.assertTrue(all(numpy.array_equal(original, new)
                        for (original, new)
                        in zip(originalQueryResults,
                               imbu.query(model, queryTerm))))


  def testCreateSaveLoadCioWordFingerprint(self):
    self._exerciseModelLifecycle("CioWordFingerprint")


  def testCreateSaveLoadCioDocumentFingerprint(self):
    self._exerciseModelLifecycle("CioDocumentFingerprint")


  def testCreateSaveLoadKeywords(self):
    self._exerciseModelLifecycle("Keywords")


  def testCreateSaveLoadSensorNetwork(self):
    self._exerciseModelLifecycle(
      "HTM_sensor_knn",
      networkConfigName="imbu_sensor_knn.json")


  def testCreateSaveLoadSensorSimpleTPNetwork(self):
    self._exerciseModelLifecycle(
      "HTM_sensor_simple_tp_knn",
      networkConfigName="imbu_sensor_simple_tp_knn.json",
      retina="en_associative_64_univ")


  def testCreateSaveLoadSensorTMSimpleTPNetwork(self):
    self._exerciseModelLifecycle(
      "HTM_sensor_tm_simple_tp_knn",
      networkConfigName="imbu_sensor_tm_simple_tp_knn.json",
      retina="en_associative_64_univ")


  def testMappingModelNamesToModelTypes(self):
    imbu = ImbuModels(dataPath=self.dataPath)

    for modelName, mappedName in imbu.modelMappings.iteritems():
      self.assertEqual(mappedName, imbu._mapModelName(modelName),
        "Incorrect mapping returned for model named '{}'".format(modelName))

    self.assertRaises(ValueError, imbu._mapModelName, "fakeModel")


  def _checkNLPObjectParams(self, nlpObject, paramsToCheck):
    for key, value in paramsToCheck.iteritems():
      param = getattr(nlpObject, key)
      self.assertEqual(value, param,
        "The {} param for {} is not as expected.".format(key, repr(nlpObject)))


  def testSetParamsInModelFactory(self):
    imbu = self._setupFakeImbuModelsInstance()

    checkpointLocation = self._createTempModelCheckpoint()

    # Base set of required Cio params to check (in the encoder)
    cacheRoot = "fake_cache_root"
    paramsToCheck = dict(
      retina="en_associative",
      apiKey=os.environ.get("CORTICAL_API_KEY"),
      retinaScaling=1.0,
    )

    # Create Cio models and check their special params
    model = imbu.createModel("CioWordFingerprint",
                             loadPath="",
                             savePath=checkpointLocation)
    paramsToCheck.update(fingerprintType=EncoderTypes.word)
    self._checkNLPObjectParams(model.getEncoder(), paramsToCheck)

    self.assertEqual(
      "fake_cache_root",
      getattr(model.getEncoder().client, "cacheDir"),
      "ImbuModels did not set the Cio encoder cache dir properly for {} model.".
      format(repr(model)))

    model = imbu.createModel("CioDocumentFingerprint",
                             loadPath="",
                             savePath=checkpointLocation)
    paramsToCheck.update(fingerprintType=EncoderTypes.document)
    self._checkNLPObjectParams(model.getEncoder(), paramsToCheck)
    self.assertEqual(
      "fake_cache_root",
      getattr(model.getEncoder().client, "cacheDir"),
      "ImbuModels did not set the Cio encoder cache dir properly for {} model.".
      format(repr(model)))

    # Create HTM Network model and check Imbu specific config params
    model = imbu.createModel("HTMNetwork",
                             loadPath="",
                             savePath=checkpointLocation,
                             networkConfigName="imbu_sensor_knn.json")
    networkConfig = getattr(model, "networkConfig")
    self.assertEqual(
      "pctOverlapOfInput",
      networkConfig["classifierRegionConfig"]["regionParams"]["distanceMethod"],
      "HTM Network model specifies an incorrect distance metric for Imbu.")
    self.assertEqual(
      "fake_cache_root",
      getattr(model.getEncoder().client, "cacheDir"),
      "ImbuModels did not set the Cio encoder cache dir properly for {} model.".
      format(repr(model)))

    # Create Keywords model and check specific params
    model = imbu.createModel("Keywords",
                             loadPath="",
                             savePath=checkpointLocation)
    paramsToCheck = dict(k=10*len(imbu.dataDict))
    self._checkNLPObjectParams(model.getClassifier(), paramsToCheck)


  def testCacheDirProperty(self):
    imbu = ImbuModels(dataPath=self.dataPath)

    checkpointLocation = self._createTempModelCheckpoint()

    model = imbu.createModel("HTMNetwork",
                             loadPath="",
                             savePath=checkpointLocation,
                             networkConfigName="imbu_sensor_knn.json")

    # Test for default cache directory
    encoder = model.getEncoder()
    defaultCacheLocation = "nupic.research/htmresearch/encoders/CioCache"
    self.assertIn(
      defaultCacheLocation,
      getattr(encoder.client, "cacheDir"),
      "Cio encoder cache dir is not the expected default location.")

    # Now explicitly set the cache directory
    encoder.cacheDir = "fake_cache_root"
    self.assertEqual(
      "fake_cache_root",
      getattr(encoder.client, "cacheDir"),
      "Cio encoder cache dir did not set properly.")


  def _checkResultsFormatting(self, results, modelName, windowSize=0):
    for result in results.values():
      self.assertEqual(
        ["indices", "scores", "text", "windowSize"], sorted(result),
        "Results dict for {} has incorrect keys.".format(modelName))
      self.assertEqual(windowSize, result["windowSize"],
        "Results give incorrect window size for {} model.".format(modelName))

      # Assert models have correct number of scores in each result
      # TODO: use ImbuModels.documentLevel
      if "Cio" in modelName:
        # Doc-level models
        self.assertEqual(1, len(result["scores"]),
          "Doc-level models should have one score per result.")
        scores = result["scores"]
      else:
        # Word-level models
        scores = result["scores"]
        textList = result["text"].split(" ")
        self.assertEqual(len(scores), len(textList),
          "Word-level models should give equal number of scores and tokens.")


  def testResultsFormatting(self):
    imbu = self._setupFakeImbuModelsInstance()

    query = "Hello world!"
    distanceArray = numpy.random.rand(35)
    idList = range(27) + [x+1000 for x in xrange(8)]

    # Test the models with windows length 10
    modelName = "HTM_sensor_simple_tp_knn"
    results = imbu.formatResults(modelName, query, distanceArray, idList)
    self._checkResultsFormatting(results, modelName, windowSize=10)
    modelName = "HTM_sensor_tm_simple_tp_knn"
    results = imbu.formatResults(modelName, query, distanceArray, idList)
    self._checkResultsFormatting(results, modelName, windowSize=10)

    # Test a word-level model
    modelName = "HTM_sensor_knn"
    results = imbu.formatResults(modelName, query, distanceArray, idList)
    self._checkResultsFormatting(results, modelName, windowSize=1)

    # Test a document-level model
    modelName = "CioDocumentFingerprint"
    distanceArray = numpy.random.rand(2)
    idList = range(1)
    results = imbu.formatResults(modelName, query, distanceArray, idList)
    self._checkResultsFormatting(results, modelName)


  def testMergeRanges(self):
    """ Tests the mergeRanges() method used in fragmenting Imbu results."""
    imbu = self._setupFakeImbuModelsInstance()

    ranges = [[3, 7], [3, 5], [0, 4]]
    self.assertSequenceEqual([[0, 7]], list(imbu._mergeRanges(ranges)))
    ranges = [[5, 6], [3, 4], [1, 2]]
    self.assertSequenceEqual([[1, 2], [3, 4], [5, 6]],
      list(imbu._mergeRanges(ranges)))
    ranges = [[0, 13]]
    self.assertSequenceEqual(ranges, list(imbu._mergeRanges(ranges)))
    ranges = [[0, 3], [6, 3]]
    with self.assertRaises(ValueError):
      list(imbu._mergeRanges(ranges))


  def testFragmentingResults(self):
    imbu = self._setupFakeImbuModelsInstance()

    lengthDoc0 = len(imbu.dataDict[0][0].split(" "))
    lengthDoc1 = len(imbu.dataDict[1][0].split(" "))

    checkpointLocation = self._createTempModelCheckpoint()

    # Test fragmenting documents with Keywords (word-level) model
    model = imbu.createModel("Keywords",
                             loadPath="",
                             savePath=checkpointLocation)

    # Test for several fragmenting scenarios; fragments for doc 1 should always
    # be the full document.
    # Query --> doc 0 fragment is based off of first token
    query = "showers"
    _, unSortedIds, unSortedDistances = imbu.query(model, query)
    resultsFrags = imbu.formatResults(
      "Keywords", query, unSortedDistances, unSortedIds)
    self.assertSequenceEqual([[0, 21]], resultsFrags[0]["indices"],
      "Incorrect fragment indices for '{}' query.".format(query))
    self.assertSequenceEqual([[0, lengthDoc1]], resultsFrags[1]["indices"],
      "Incorrect fragment indices for '{}' query.".format(query))

    # Query --> no max score in the results, so no fragmenting of documents
    query = "work"
    _, unSortedIds, unSortedDistances = imbu.query(model, query)
    resultsFrags = imbu.formatResults(
      "Keywords", query, unSortedDistances, unSortedIds)
    self.assertSequenceEqual([[0, lengthDoc0]], resultsFrags[0]["indices"],
      "Incorrect fragment indices for '{}' query.".format(query))
    self.assertSequenceEqual([[0, lengthDoc1]], resultsFrags[1]["indices"],
      "Incorrect fragment indices for '{}' query.".format(query))

    # Query --> doc 0 fragment is based off of middle token
    query = "lunchtime"
    _, unSortedIds, unSortedDistances = imbu.query(model, query)
    resultsFrags = imbu.formatResults(
      "Keywords", query, unSortedDistances, unSortedIds)
    self.assertSequenceEqual([[9, lengthDoc0]], resultsFrags[0]["indices"],
      "Incorrect fragment indices for '{}' query.".format(query))
    self.assertSequenceEqual([[0, lengthDoc1]], resultsFrags[1]["indices"],
      "Incorrect fragment indices for '{}' query.".format(query))

    # Results for doc-level model should not be fragmented
    model = imbu.createModel("CioDocumentFingerprint",
                             loadPath="",
                             savePath=checkpointLocation)
    query = "unicorn"
    _, unSortedIds, unSortedDistances = imbu.query(model, query)
    resultsFrags = imbu.formatResults(
      "CioDocumentFingerprint", query, unSortedDistances, unSortedIds)
    self.assertSequenceEqual([[0, lengthDoc0]], resultsFrags[0]["indices"],
      "Incorrect fragment indices for '{}' query.".format(query))
    self.assertSequenceEqual([[0, lengthDoc1]], resultsFrags[1]["indices"],
      "Incorrect fragment indices for '{}' query.".format(query))

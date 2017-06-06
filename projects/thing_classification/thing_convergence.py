# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2016, Numenta, Inc.  Unless you have an agreement
# with Numenta, Inc., for a separate license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero Public License for more details.
#
# You should have received a copy of the GNU Affero Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------

"""
This file is used to run Thing experiments using simulated sensations.
"""
import random
import os
import numpy as np
import pprint
from htmresearch.support.logging_decorator import LoggingDecorator
from htmresearch.frameworks.layers.l2_l4_inference import (
  L4L2Experiment, rerunExperimentFromLogfile)

from htmresearch.frameworks.layers.object_machine_factory import (
  createObjectMachine
)

def loadThingObjects(numCorticalColumns=1):
  """
  Load simulated sensation data on a number of different objects
  There is one file per object, each row contains one feature, location pairs
  The format is as follows
  [(-33.6705, 75.5003, 2.4207)/10] => [[list of active bits of location],
                                       [list of active bits of feature]]
  The content before "=>" is the true 3D location / sensation
  The number of active bits in the location and feature is listed after "=>".
  @return A simple object machine
  """
  # create empty simple object machine
  objects = createObjectMachine(
    machineType="simple",
    numInputBits=20,
    sensorInputSize=1024,
    externalInputSize=1024,
    numCorticalColumns=numCorticalColumns,
    numFeatures=0,
    numLocations=0,
  )

  for _ in range(numCorticalColumns):
    objects.locations.append([])
    objects.features.append([])

  objDataPath = 'data/'
  objFiles = [f for f in os.listdir(objDataPath)
               if os.path.isfile(os.path.join(objDataPath, f))]

  idx = 0
  for f in objFiles:
    objName = f.split('.')[0]
    objFile = open('{}/{}'.format(objDataPath, f))

    sensationList = []
    for line in objFile.readlines():
      # parse thing data file and extract feature/location vectors
      sense = line.split('=>')[1].strip(' ').strip('\n')
      location = sense.split('],[')[0].strip('[')
      feature = sense.split('],[')[1].strip(']')
      location = np.fromstring(location, sep=',', dtype=np.uint8)
      feature = np.fromstring(feature, sep=',', dtype=np.uint8)

      # add the current sensation to object Machine
      sensationList.append((idx, idx))
      for c in range(numCorticalColumns):
        objects.locations[c].append(set(location.tolist()))
        objects.features[c].append(set(feature.tolist()))
      idx += 1
    objects.addObject(sensationList, objName)
  return objects



def trainNetwork(objects, numColumns):
  exp = L4L2Experiment("shared_features",
                       numCorticalColumns=numColumns)
  exp.learnObjects(objects.provideObjectsToLearn())

  settlingTime = 3
  L2Representations = exp.objectL2Representations
  print "Learned object representations:"
  pprint.pprint(L2Representations, width=400)
  print "=========================="

  # For inference, we will check and plot convergence for each object. For each
  # object, we create a sequence of random sensations for each column.  We will
  # present each sensation for settlingTime time steps to let it settle and
  # ensure it converges.
  for objectId in objects:
    obj = objects[objectId]

    objectSensations = {}
    for c in range(numColumns):
      objectSensations[c] = []

    if numColumns > 1:
      # Create sequence of random sensations for this object for all columns At
      # any point in time, ensure each column touches a unique loc,feature pair
      # on the object.  It is ok for a given column to sense a loc,feature pair
      # more than once. The total number of sensations is equal to the number of
      # points on the object.
      for sensationNumber in range(len(obj)):
        # Randomly shuffle points for each sensation
        objectCopy = [pair for pair in obj]
        random.shuffle(objectCopy)
        for c in range(numColumns):
          # stay multiple steps on each sensation
          for _ in xrange(settlingTime):
            objectSensations[c].append(objectCopy[c])

    else:
      # Create sequence of sensations for this object for one column. The total
      # number of sensations is equal to the number of points on the object. No
      # point should be visited more than once.
      objectCopy = [pair for pair in obj]
      # random.shuffle(objectCopy)
      for pair in objectCopy:
        # stay multiple steps on each sensation
        for _ in xrange(settlingTime):
          objectSensations[0].append(pair)

    inferConfig = {
      "object": objectId,
      "numSteps": len(objectSensations[0]),
      "pairs": objectSensations,
      "includeRandomLocation": False,
    }

    inferenceSDRs = objects.provideObjectToInfer(inferConfig)
    exp.infer(inferenceSDRs, objectName=objectId, reset=False)
    print "Output for {}: {}".format(objectId, exp.getL2Representations())
    for i in range(len(objects)):
      print "Intersection with {}:{}".format(
        objectId,
        len(exp.getL2Representations()[0] &
            L2Representations[objects.objects.keys()[i]][0]))
    exp.sendReset()



if __name__ == "__main__":
  numColumns = 1
  objects = loadThingObjects(numColumns)

  trainNetwork(objects, numColumns)




from pymel.core.datatypes import Vector
from random import random
import math
BASE_THICKNESS = 0.005
THICKNESS_EXP = 2.0

class Node:
    idCount = 1
    
    def __init__(self, vec):
        self.position = vec
        self.children = []
        self.id = Node.idCount
        Node.idCount = Node.idCount + 1
    
    def __hash__(self):
        return self.id
    
    def __eq__(self, other):
        return self.id == other.id

def drawPoints(points):
    group = cmds.group(em=True, n="points")
    for point in points:
        sphere = cmds.polySphere(sx=5, sy=5, r=0.01)
        cmds.xform(t=(point[0], point[1], point[2]))
        cmds.parent(sphere, group)
          
def pointsInsideMesh(mesh, regionMin, regionMax, numPoints):
    hits = 0
    cmds.makeIdentity(mesh, apply=True, rotate=True, translate=True, scale=True)
    pointsInsideMesh = []
    cpomNode = cmds.createNode("closestPointOnMesh")
    cmds.connectAttr(mesh+".outMesh", cpomNode+".inMesh")
    regionDistance = regionMax - regionMin
    while hits < numPoints:
        point = regionMin + Vector(random() * regionDistance[0], random() * regionDistance[1], random() * regionDistance[2])
        cmds.setAttr(cpomNode + ".inPosition", point[0], point[1], point[2], type="double3")
        cpomPosition = Vector(cmds.getAttr(cpomNode + ".position"))
        cpomNormal = Vector(cmds.getAttr(cpomNode + ".normal"))

        difference = cpomPosition - point

        if Vector.dot(cpomNormal, difference) > 0:
            hits = hits + 1
            pointsInsideMesh.append(point)

    return pointsInsideMesh

def findNearestNode(position, node):
    if len(node.children) == 0:
        return node
    min_distance = math.sqrt((node.position - position).sqlength())
    nearest_node = node
    for child in node.children:
        nearestNodeInChild = findNearestNode(position, child)
        distance = math.sqrt((nearestNodeInChild.position - position).sqlength())
        if distance < min_distance:
            min_distance = distance
            nearest_node = nearestNodeInChild
    return nearest_node

def spaceColonization(root, pointsInsideMesh, iters):
    for i in range(1, iters):
        dictoniary = {}
        alivePoints = []
        for point in pointsInsideMesh:
            nearestNode = findNearestNode(point, root)
            distance =  math.sqrt((nearestNode.position - point).sqlength())
            # Won't append to replacement list if this doesnt happen, so points 
            # that reached kill distance are not preserved
            if distance > KILL_DISTANCE:
                alivePoints.append(point)
                if distance <= INFLUENCE_DISTANCE:
                    if nearestNode not in dictoniary:
                        dictoniary[nearestNode] = []
                    dictoniary[nearestNode].append(point)
        # Only preserve points whose kill distance hasn't been reached
        pointsInsideMesh = alivePoints
        for node in dictoniary:
            averageDirection = Vector(0, 0, 0)
            for attractionPoint in dictoniary[node]:
                attractionDirection = (attractionPoint - node.position)
                attractionDirection.normalize()
                averageDirection = averageDirection + attractionDirection / len(dictoniary[node])
            node.children.append(Node(node.position + averageDirection * GROWTH_DISTANCE))

def treeToArray(node):
    list = [node.position]
    if len(node.children) == 0:
        return list
    for child in node.children:
        list = list + treeToArray(child)
    return list

def vecToTup(vec):
    return (vec[0], vec[1], vec[2])

def drawCurves(node):
    group = cmds.group(em=True, n="curves")
    naiveCurves(node, group)

def naiveCurves(node, group):
    if len(node.children) == 0:
        return
    for child in node.children:
        curve = cmds.curve(d=1, p=[vecToTup(node.position), vecToTup(child.position)])
        cmds.parent(curve, group)
        naiveCurves(child, group)
    
def printDict(dict, iter):
    print "iteration:", iter
    for node in dict:
        print "parent:", node.position, node.id
        print "nearest:", dict[node]

def treeString(node):
    if len(node.children) == 0:
        return "{" + str(node.id) + "}"
    childText = ""
    for child in node.children:
        childText += treeString(child) + ","
    return "{" + str(node.id) + ":[" + childText + "]}"
    
def extrudeCurve(curve, thickness):
    arrPos = cmds.pointOnCurve(curve, p=True)
    position = Vector(arrPos[0], arrPos[1], arrPos[2])
    arrTangent = cmds.pointOnCurve(curve, nt=True)
    tangent = Vector(arrTangent[0], arrTangent[1], arrTangent[2])
    cylinder = cmds.polyCylinder(
        radius=thickness/2, 
        axis=tangent,
        height=0.001,
        sx=8,
        sy=1,
        sz=1,
    )[0]
    cmds.xform(t=position)
    curveSpans = cmds.getAttr(curve+'.spans')
    cmds.polyExtrudeFacet(
        cylinder + '.f[16:23]',
        inputCurve=curve,
        kft=True,
        pvt=position,
        divisions=curveSpans,
    )
    cmds.polyExtrudeFacet(
        cylinder + '.f[16:23]',
        kft=True,
        divisions=1,
        offset=thickness/4,
        ltz=thickness/2 * 1.5
    )
    return cylinder

def extrudeCurveMainTrunk(curve, thickness, taper):
    arrPos = cmds.pointOnCurve(curve, p=True)
    position = Vector(arrPos[0], arrPos[1], arrPos[2])
    arrTangent = cmds.pointOnCurve(curve, nt=True)
    tangent = Vector(arrTangent[0], arrTangent[1], arrTangent[2])
    cylinder = cmds.polyCylinder(
        radius=thickness/2 * (1.0 / taper), 
        axis=tangent,
        height=0.001,
        sx=8,
        sy=1,
        sz=1,
    )[0]
    cmds.xform(t=position)
    curveSpans = cmds.getAttr(curve+'.spans')
    cmds.polyExtrudeFacet(
        cylinder + '.f[16:23]',
        inputCurve=curve,
        kft=True,
        pvt=position,
        divisions=curveSpans * 2,
        taper=taper
    )
    cmds.polyExtrudeFacet(
        cylinder + '.f[16:23]',
        kft=True,
        divisions=1,
        offset=thickness/4,
        ltz=thickness/2 * 1.5
    )
    return cylinder
    
def buildBranches(node, group):
    if len(node.children) == 0:
        return (BASE_THICKNESS, [node.position])
    if len(node.children) == 1:
        thickness, points = buildBranches(node.children[0], group)
        return (thickness, [node.position] + points)
    if len(node.children) > 1:
        thickness = 0.0
        for child in node.children:
            childThickness, childPoints = buildBranches(child, group)
            points = [node.position] + childPoints
            thickness = thickness + math.pow(childThickness, THICKNESS_EXP)
            curve = cmds.curve(n="branchCurve", d=1, p=points)
            curveSpans = cmds.getAttr(curve + '.spans')
            cmds.rebuildCurve(curve, d=3, end=True, kep=True,  kt=True, s=curveSpans * 2)
            cylinder = extrudeCurve(curve, childThickness)
            cmds.parent(curve, group)
            cmds.parent(cylinder, group)
        return (math.pow(thickness, 1.0/THICKNESS_EXP), [node.position])
            
def buildTopology(node, groupName):
    group = cmds.group(em=True, n=groupName)
    thickness, points = buildBranches(node, group)
    curve = cmds.curve(n="branchCurve", d=3, p=points)
    curveSpans = cmds.getAttr(curve + '.spans')
    cmds.rebuildCurve(curve, d=3, end=True, kep=True,  kt=True, s=curveSpans * 2)    
    cylinder = extrudeCurveMainTrunk(curve, thickness, 0.7)
    cmds.parent(curve, group)
    cmds.parent(cylinder, group)



# Main code

KILL_DISTANCE = 0.1
INFLUENCE_DISTANCE = 1.0
GROWTH_DISTANCE = 0.1

mesh = "mesh"
regionMin = Vector(-1, 0, 1)
regionMax = Vector(1, 2, -1)
numPoints = 500
attractionPoints = []

attractioinPoints = pointsInsideMesh(mesh, regionMin, regionMax, numPoints)

node = Node(Vector(0, 0.0, 0))

spaceColonization(node, attractioinPoints, 200)

buildTopology(node, "tree")

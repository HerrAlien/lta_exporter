#!BPY

"""
Name: 'Lithtech ASCII (.lta) with anims ...'
Blender: 246
Group: 'Export'
Tooltip: 'Export selected meshes to Lithtech ASCII file format (.lta) while preserving animation data'
"""

__author__ = "Herr_Alien"
__version__ = "1.0"
__bpydoc__ = """\
This script exports meshes to the Lithtech ASCII format used in many
Monolith games.

The model must be converted to triangles (ctrl + t in edit mode) before
exporting

Once exported the model can be opened with ModelEdit and compiled into an
LTB/abc model.

The mesh is exported with the scene root at the origin, which determines
where the model will be connected to the parent socket.  Rotation and
translation can be corrected in Blender through trial and error or in the
.lta file itself.

UV maps are rendered as if the normals were reversed.  In most cases this
isn't noticeable unless you are working with text for some reason (it will
appear as mirror writing).

Limitations:

Usage:
\n\tSelect meshes to be exported in object mode and run this script from
the "File->Export" menu.
"""


# --------------------------------------------------------------------------
# LTA Export v1.0 by Herr_Alien
# --------------------------------------------------------------------------
# ***** BEGIN GPL LICENSE BLOCK *****
#
# Copyright (C) 2010: Herr_Alien - garone80@yahoo.com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# ***** END GPL LICENCE BLOCK *****
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Herr_Alien < garone80@yahoo.com >
#   - corrected the behavior of saving vertex information (now a vertex is
#     written to the .LTA file only once)
#   - if two different vertices overlap, only one will get written
#     (thanks, Coty!) 
# --------------------------------------------------------------------------

import Blender
import math
from Blender import Armature




def export_lta2(filepath):

    print "\nExporting LTA... "
    meshObjectList = []
    objectList = []
    scene = Blender.Scene.GetCurrent()

# ------- this is where all the objects are
    objectList = scene.getChildren()

    for obj in objectList:
      if obj != None and obj.getType()=='Mesh':
        mesh = obj.getData(False, True) # we want only meshes
        if mesh != None:
          for face in mesh.faces:
            if len(face.v) > 3:
              raise(mesh.name + " can't be exported: please convert the model to triangles\
(ctrl + t) before exporting")

          meshObjectList.append(mesh)

    
    out = file(filepath, 'w')
    out.write('''(lt-model-0
''')
    bns = writeOnLoadCmds(out, meshObjectList, scene)
# write the bone hierarchy
    writeBoneHierarchy(out, bns)
#write the shapes
    writeShapes(out, meshObjectList)
# write the animations
    writeAnimations(out, bns)
        
    out.write('''
)''')
    out.close()

    print "Done!"

#-------------------------------------------------------------------------------
# writes the on-load-cmds section 
# @param filestream the file output strea,
# @param meshObjectList the list of geometry parts
# @param scene the whole Blender scene
#-------------------------------------------------------------------------------
def writeOnLoadCmds(filestream, meshObjectList, scene):
  filestream.write('''  (on-load-cmds 
    (''')
# anim-bindings
  writeAnimBindings(filestream, meshObjectList, scene)
# set-node-flags

## get all bones
  skel = getArmature()
  bns = []
  if (None != skel):
    bns = skel.bones.values()

  writeSetNodesFlags(filestream, meshObjectList, scene, bns)
#write lods
  writeDefaultLODs(filestream, meshObjectList, scene)
# add-deformer
  writeDeformers(filestream, meshObjectList, scene, bns)
  filestream.write('''
    )
  )''')
  return bns

def getArmature():
  bns = []          #### the list of bones of skeleton
  skel = None       #### skel
  arms = Armature.Get().values()
  for arm in arms:
    # get all them bones
    bns = arm.bones.values()
    if(len(bns) > 0):
      skel = arm
      break
  return skel


def writeShapes(filestream, meshObjectList):
  threshold = 0.0000000001
  for mesh in meshObjectList:
    uniqueVertexList = []
    filestream.write('''
  (shape "''')
    filestream.write(mesh.name)
    filestream.write('''" 
		(geometry 
			(mesh "''')
    filestream.write(mesh.name)
    filestream.write('''"''') 

    #### exporting the vertices
    filestream.write('''
        (vertex 
          (
''')
    for face in mesh.faces:
      v1, v2, v3 = face.v
      exportUniqueVertex(filestream, v1, uniqueVertexList, threshold)
      exportUniqueVertex(filestream, v2, uniqueVertexList, threshold)
      exportUniqueVertex(filestream, v3, uniqueVertexList, threshold)

    filestream.write('''
          )
        )''')
    #### end of vertices
    
    #### exported the list of vertices. Move on to uv's
    filestream.write('''
        (uvs
          (
    ''')
    # see if the mesh has UVs to begin with ...
    if mesh.faceUV:           # if we have UV's ...
      for face in mesh.faces: #
        for uv in face.uv:    # write'm down!
          uv = tuple(uv)
          uv = uv[0], 1 - uv[1]
          filestream.write('            (%f %f )\n' % uv)
    filestream.write('''
          )
        )''')
    #### end of UVs
    
    #### export tex-fs
    x = 0 
    filestream.write('''
        (tex-fs
          (''')
    for face in mesh.faces:
      filestream.write('%i %i %i ' % (x, x + 1, x + 2))
      x += 3

    filestream.write(''')
        )''')
    #### end of tex-fs
    
    #### export tri-fs
    filestream.write('''
        (tri-fs
          (''')
    
    for face in mesh.faces:
  # ------------------------------------------------
  # Herr_Alien:
  #  - and for each face, I try to find the
  #    vertex index in my list
  #  - I then write the index found to the .LTA file
  # ------------------------------------------------
      v1, v2, v3 = face.v
      v1Index = 0;
      v2Index = 0;
      v3Index = 0;
        
      if v1 not in uniqueVertexList:
        faceverts = tuple(v1.co)
        for vx in uniqueVertexList:
          vxCoords = tuple(vx.co)
          if math.fabs(faceverts[0]-vxCoords[0]) < threshold and math.fabs(faceverts[1]-vxCoords[1]) < threshold and math.fabs(faceverts[2]-vxCoords[2]) < threshold:
            break
          v1Index = v1Index+1          
      else:
        v1Index = uniqueVertexList.index(v1)

      if v2 not in uniqueVertexList:
        faceverts = tuple(v2.co)
        for vx in uniqueVertexList:
          vxCoords = tuple(vx.co)
          if math.fabs(faceverts[0]-vxCoords[0]) < threshold and math.fabs(faceverts[1]-vxCoords[1]) < threshold and math.fabs(faceverts[2]-vxCoords[2]) < threshold:
            break
          v2Index = v2Index+1          
      else:
        v2Index = uniqueVertexList.index(v2)
        
      if v3 not in uniqueVertexList:
        faceverts = tuple(v3.co)
        for vx in uniqueVertexList:
          vxCoords = tuple(vx.co)
          if math.fabs(faceverts[0]-vxCoords[0]) < threshold and math.fabs(faceverts[1]-vxCoords[1]) < threshold and math.fabs(faceverts[2]-vxCoords[2]) < threshold:
            break
          v3Index = v3Index+1          
      else:
        v3Index = uniqueVertexList.index(v3)

      filestream.write('%i %i %i ' % (v1Index, v2Index, v3Index))

    
    filestream.write(''')
        )''')        
    #### end of tri-fs
    ############## end of shape export ########################
    filestream.write('''
			)
    )
  )''')


def exportUniqueVertex(filestream, vert, vertexList, threshold):
  if vert not in vertexList:
    faceverts = tuple(vert.co)
    foundByCoordinates = False
    for vx in vertexList:
      vxCoords = tuple(vx.co)
      if math.fabs(faceverts[0]-vxCoords[0]) < threshold and math.fabs(faceverts[1]-vxCoords[1]) < threshold and math.fabs(faceverts[2]-vxCoords[2]) < threshold:
        foundByCoordinates = True
        break
    if not foundByCoordinates:
      filestream.write('            (%f %f %f )\n' % faceverts)
      vertexList.append(vert)



#--------------------------------------------
# @param bns the list of bones
#--------------------------------------------
def writeBoneHierarchy(filestream, bns):
  filestream.write('''
      (hierarchy
        (children
          (
            (transform "Scene Root"  
              (matrix  
                ( 
                  (1 0 0 0)
                  (0 1 0 0)
                  (0 0 1 0)
                  (0 0 0 1)
                ) 
              ) 
              (children  
                ( 
''')
  rootBone = None
  
  for bn in bns:
    if (False == bn.hasParent()):
      rootBone = bn
      break
      
  if None == rootBone: # no bones in our model ...
  # we'll do a fake structure. One bone (except Scene Root), weighting with 1 all vertices.
    filestream.write('''
    (transform "Bone" 
      (matrix
        (
          (1 0 0 0)
          (0 1 0 0)
          (0 0 1 0)
          (0 0 0 1)
        )
      )
    )''') 
   
  else: # this one is recursive
    writeBone(filestream, rootBone)
    
  filestream.write('''
                )
              )
            )
          )
        )
      )''')
#--------------------------------------------
def writeBone(filestream, bn):
  filestream.write('''(transform "''')
  filestream.write(bn.name)
  filestream.write('''" 
  (matrix
    (
      ''')
  
  #str(bn.matrix['ARMATURESPACE'])
  myMatrix = bn.matrix['ARMATURESPACE']
  filestream.write("(")
  filestream.write(str(myMatrix[0][0]))
  filestream.write(" ")
  filestream.write(str(myMatrix[0][1]))
  filestream.write(" ")
  filestream.write(str(myMatrix[0][2]))
  filestream.write(" ")
  filestream.write(str(myMatrix[0][3]))
  filestream.write(")")
  filestream.write('''
  ''')
  filestream.write("(")
  filestream.write(str(myMatrix[1][0]))
  filestream.write(" ")
  filestream.write(str(myMatrix[1][1]))
  filestream.write(" ")
  filestream.write(str(myMatrix[1][2]))
  filestream.write(" ")
  filestream.write(str(myMatrix[1][3]))
  filestream.write(")")
  filestream.write('''
  ''')
  filestream.write("(")
  filestream.write(str(myMatrix[2][0]))
  filestream.write(" ")
  filestream.write(str(myMatrix[2][1]))
  filestream.write(" ")
  filestream.write(str(myMatrix[2][2]))
  filestream.write(" ")
  filestream.write(str(myMatrix[2][3]))
  filestream.write(")")
  filestream.write('''
  ''')
  filestream.write("(")
  filestream.write(str(myMatrix[3][0]))
  filestream.write(" ")
  filestream.write(str(myMatrix[3][1]))
  filestream.write(" ")
  filestream.write(str(myMatrix[3][2]))
  filestream.write(" ")
  filestream.write(str(myMatrix[3][3]))
  filestream.write(")")

  filestream.write('''
    )
  )''') #matrix
  #see if it has kids
  if(bn.hasChildren()):
    filestream.write('''
    (children
      (
        ''')
    
    for kidBone in bn.children:
      writeBone(filestream, kidBone)
    
    filestream.write('''
      )
    )''')
  filestream.write(''')''') #transform
  
  

def writeDeformers(filestream, meshObjectList, scene, bns):
  #list of al bones names
  bnsNames = []
  for bn in bns:
    bnsNames.append(bn.name)
    
  for msh in meshObjectList:
    filestream.write('''
      (add-deformer
        (skel-deformer 
					(target "''')
    filestream.write(msh.name)
    filestream.write('''")''')
		
    filestream.write('''
          (influences 
						(''')
    if(len(bns) > 0):
      for bn in bns:
        filestream.write('"')
        filestream.write(bn.name)
        filestream.write('" ')
		
    else:
      filestream.write('"Bone"')
      
    filestream.write(''')
					)''')
		
		#get the influences
    filestream.write('''
          (weightsets 
            (''')
            
    noVerts = len(msh.verts)
    print noVerts
    for i in range (0, noVerts):
      infls = msh.getVertexInfluences(i)
      filestream.write('''
              (''')
      if(len(bns) > 0):
        for infl in infls:
          bnName = infl[0]
          foundBoneIndex = bnsNames.index(bnName, 0)
          filestream.write(str(foundBoneIndex))
          filestream.write(' ')
          filestream.write(str(infl[1]))
          filestream.write(' ')
      else:
        filestream.write("0 1")
   
      filestream.write(')')
      
    filestream.write('''
            ) 
          )''')
    filestream.write('''
        )
      )''')
		  

#-------------------------------------------------------------------------------
# writes the lod-groups from the on-load-cmds section 
# @param filestream the file output strea,
# @param meshObjectList the list of geometry parts
# @param scene the whole Blender scene
#-------------------------------------------------------------------------------
def writeDefaultLODs(filestream, meshObjectList, scene):
  filestream.write('''
      (lod-groups 
        (''')          
  for msh in meshObjectList:
    mshName = msh.name
    filestream.write('''
          (create-lod-group "''')
    filestream.write(mshName)
    filestream.write('''"
            (lod-dists 
              (0.000000 )
            )
            (shapes 
              ("''')
    filestream.write(mshName)
    filestream.write('''") 
            )
          )''' )                
  filestream.write('''
        )
      )''')
        

#-------------------------------------------------------------------------------
# writes the anim-bindings from the on-load-cmds section 
# @param filestream the file output strea,
# @param meshObjectList the list of geometry parts
# @param scene the whole Blender scene
#-------------------------------------------------------------------------------
def writeAnimBindings(filestream, meshObjectList, scene):
  filestream.write('''
      (anim-bindings 
        (''')
  actions = Blender.Armature.NLA.GetActions().values()      
  if(len(actions) > 0 ):
    for actn in actions:
      writeAnimBinding(filestream, actn.getName())
  else:
    writeAnimBinding(filestream, "Animation")
    
  filestream.write('''
        )
      )''')

#-------------------------------------------
# writes one anim binding entry
#-------------------------------------------
def writeAnimBinding(filestream, actionName):
  filestream.write('''
          (anim-binding
            (name "''')
  filestream.write(actionName)
  filestream.write('''")
            (dims 
              (1.000000 1.000000 1.000000 )
            )
            (translation 
              (0.000000 0.000000 0.000000 )
            )
            (interp-time 0 )
          )''')


def writeSetNodesFlags(filestream, meshObjectList, scene, bns):
  filestream.write('''
      (set-node-flags
        (
          ("Scene Root" 0)''')
  if (len (bns) > 0):
    for bn in bns:
        #write the name and the 0 flag
      filestream.write('''
          ("''')
      filestream.write(bn.name)
      filestream.write('''" 0)''')
  
  else:
    filestream.write('''
          ("Bone" 0)
          ''')
    
  filestream.write('''
        )
      )''')
      
      
      
def writeAnimations(filestream, bones):

  actions = Blender.Armature.NLA.GetActions().values()
  if(len(actions) > 0):
    # do stuff ...
    arm = None
    armName = getArmature().name
    
    for obj in Blender.Scene.GetCurrent().objects:
      if (obj != None and obj.getType() == 'Armature'):
        arm = obj
    
    for action in actions:
      writeAnimation(filestream, action, arm, bones)
      
  else: # add a hardcoded one ...
    filestream.write('''
  (animset "Animation"  
    (keyframe  
      (keyframe  
        (times  
          (0 ) 
        ) 
        (values  
          ("" ) 
        ) 
      ) 
    ) 
    (anims  
      ( 
        (anim  
          (parent "Scene Root" ) 
          (frames  
            (posquat  
              ( 
                ( 
                  (0.000000 0.000000 0.000000 ) 
                  (0.000000 1.000000 0.000000 0.000000 ) 
                ) 
              ) 
            ) 
          ) 
        )
        (anim  
          (parent "Bone" ) 
          (frames  
            (posquat  
              ( 
                ( 
                  (0.000000 0.000000 0.000000 ) 
                  (0.000000 1.000000 0.000000 0.000000 ) 
                ) 
              ) 
            ) 
          ) 
        )  
      ) 
    ) 
  )
''')
        


def writeAnimation(filestream, action, arm, bones):
#getFrameNumbers()
  filestream.write('''
  (animset "''')
  filestream.write(action.name)
  filestream.write('''"  
    (keyframe  
      (keyframe
      ''')
  # add times and keyframe strings
  keyFrames = action.getFrameNumbers()
  filestream.write('''  (times
          (''')
  for frameIndex in keyFrames:
    filestream.write(str(frameIndex))
    filestream.write(" ")
  
  filestream.write(''')
        )''')    
  
  filestream.write('''  (values
          (''')
  for frameIndex in keyFrames:
    filestream.write('''"" ''')
  
  filestream.write(''')
        )''')    

  filestream.write('''
      )
    )
    (anims
      (
''') #keyframes

  ##now, do the animate ...
  #1. activate the armature
  action.setActive(arm)
  
  #2. get the pose
  pose = arm.getPose()
  poseBones = pose.bones.values()
  
  animData = dict([(poseBone.name, []) for poseBone in poseBones])
  
  #3. for each frame, output the transformations
  for frameIndex in keyFrames:
    arm.evaluatePose(frameIndex)
    for poseBone in poseBones:
      posQuat = poseBone.loc, poseBone.quat
      animData[poseBone.name].append(posQuat)

  for poseBone in poseBones:
    filestream.write('''
      (anim
        (parent "''')
    filestream.write(poseBone.name)    
    filestream.write('''")
        (frames
          (posquat
            (''')
    for posQuat in animData[poseBone.name]:
      #pos = posQuat[0]
      #quat = posQuat[1]
      filestream.write('''
               (
                (''')
      filestream.write(str(posQuat[0][0]))                
      filestream.write(" ")                
      filestream.write(str(posQuat[0][1]))                
      filestream.write(" ")                
      filestream.write(str(posQuat[0][2]))                
      filestream.write(''')
                (''')

      filestream.write(str(posQuat[1][0]))                
      filestream.write(" ")                
      filestream.write(str(posQuat[1][1]))                
      filestream.write(" ")                
      filestream.write(str(posQuat[1][2]))                
      filestream.write(" ")                
      filestream.write(str(posQuat[1][3]))                
                
      filestream.write(''')
               )''')
      
    filestream.write('''
            ) 
          )
        )
      )    
    ''')

  filestream.write('''
      )
    )
  )''') #animset


Blender.Window.FileSelector(export_lta2, "Export")

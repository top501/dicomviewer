# -*- coding: utf-8 -*- 
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import dicom
import numpy as np
import scipy.ndimage
import nifti
from sys import *

ESCAPE = 27
E_CHAR = 101
FILTER = 102
LIGHTN = 108
DEPTHT = 100
BLENDT = 98
LEFTXY = 100
RIGHXY = 102
UPARYZ = 101
DOARYZ = 103
LEARXZ = 106
RIARXZ = 107

"""
An image is defined by its two dimensional data, and the size of these dimensions
Dimension are not really necessary here, as len(data) and len(data[0]) could do
it, but I think it is nicer :-)
"""
class Volume:
    def __init__(self):
        self.data = None
        self.sizeX = 0
        self.sizeY = 0
        self.sizeZ = 0
        
def loadVolume(filename):
    f = open(filename,'r')
    lines = f.readlines()
    n = len(lines)
    
    fname = lines[0].rstrip()
    image = dicom.read_file(fname)
    height = len(image.PixelArray)
    width = len(image.PixelArray[0])
    
    real_max = np.max(image.PixelArray)
    real_min = np.min(image.PixelArray)
    
    taille = np.max([height,width,n])
    
    taille = pow(2,np.ceil(np.log2(taille)))
    if(taille<256):
        taille=256
    VOL = np.zeros((taille,taille,taille))
    
    for i in range(n):
        fname = lines[i].rstrip()
        image = dicom.read_file(fname)
        tab = image.pixel_array
        VOL[i-1][0:height][0:width] = tab
        
    maximum = np.max(VOL)
    minimum = np.min(VOL)
    maxmin = maximum-minimum
    VOL = (VOL-minimum)/maxmin
    VOL = scipy.ndimage.zoom(VOL,256./taille)
    omage = Volume()
    omage.data = VOL
    omage.sizeX = 256
    omage.sizeY = 256
    omage.sizeZ = 256
    return omage
     
"""
Load the GL texture from the filename: 
basically, I load it using loadImage, and then create 3 textures with the image
I obtained.
If you do not want to use dicom, just change the function above (stay in grey values)

Principle:
Generate texture identifiers
Bind an identifier
define what to do when you upscale (MAG_FILTER) and downscale (MIN_FILTER)
then link the texture
2D texture, 0, number of channels, width, height, 0, type of data to store, type of data, data

Small change with python NeHe mipmapping : mipmap can be called from parameters
"""
def LoadGLTextures(fname):
    # Load Texture
    image1 = loadVolume(fname)
    # Create Textures
    texture = glGenTextures(1)
    
    # Linear interpolation
    glBindTexture(GL_TEXTURE_3D, texture)
    glTexEnvf( GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE )
    glTexParameterf( GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_LINEAR )
    glTexParameterf( GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER, GL_LINEAR )
    glTexImage3D(GL_TEXTURE_3D,0,GL_INTENSITY,image1.sizeX,image1.sizeY,image1.sizeZ,0, GL_LUMINANCE,GL_FLOAT,image1.data)
    return texture

"""
Canvas class : 
does all the interactions with GL and GLU. Arbitrary division, still convenient.
stores the state of the canvas (texturing, blending,...)
""" 
class Canvas:
    
    """
        Initialisation of gl parameters must be done AFTER the calls to GLUT,
        that defines some parameters to use
        So, to be sure, we just initalize the state of the canvas here
    """
    def __init__(self,t_name):
        self.notYet = True
        self.textures = None 
        self.name = t_name
        self.filter = 0;
        self.light = True
        self.blending = True
        self.depthtest = False
        self.xyrotation = 0
        self.yzrotation = 0
        self.xzrotation = 0
        
    """
        Function to be called when the canvas is resized.
        Basically, I resize the canvas and the view
    """
    def ReSizeGLScene(self,Width, Height):
        
        # 0 in width would mess up my further calculations, and you couldn't
        # see anything
        if Width == 0:
	        Width = 1

        # Resize the canvas to the size of the resized window
        glViewport(0, 0, Width, Height)
        
        #Define the projection
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity() # Reinitalisation
        aspect = float(Height)/float(Width)
        #My cube coordinates are -1.,1,-1,1,-1,1. I define the projection
        #with 5 in order to be able to see the cube and its possible rotations
        #You can change it if you want. aspect to keep the window ratio
        glOrtho(-4.,4.,-4.*aspect,4.*aspect,-100.,100.)
        glMatrixMode(GL_MODELVIEW)
    
    def initGL(self,Width,Height):
        # Loads the textures and enables 2D texturing (I only draw 2D images on
        # the cube faces)
        self.textures = LoadGLTextures(self.name)
        glEnable(GL_TEXTURE_3D)
        
        
        #Lightning stuff (I do not use it but hey why not)
        
        # white ambient light at half intensity (rgba)
        LightAmbient = [ 0.5, 0.5, 0.5, 1.0 ]
        # super bright, full intensity diffuse light.
        LightDiffuse = [ 1.0, 1.0, 1.0, 1.0 ]
        # position of light (x, y, z, (position of light))
        LightPosition = [ 0.0, 0.0, 2.0, 1.0 ]
        glLightfv(GL_LIGHT1, GL_AMBIENT, LightAmbient)  # add lighting. (ambient)
        glLightfv(GL_LIGHT1, GL_DIFFUSE, LightDiffuse)  # add lighting. (diffuse).
        glLightfv(GL_LIGHT1, GL_POSITION,LightPosition) # set light position.
        glEnable(GL_LIGHT1)  
        
        #Window is set to black
        glClearColor(0.0, 0.0, 0.0, 0.0)
        
        #Depth buffer to handle pixels being at (x,y) position. The one with
        #smallest z is printed. Initialized but disabled: obviously, it messes
        #up with GL_MAX blending
        glClearDepth(1.0)		
        glDepthFunc(GL_LESS)				
        glDisable(GL_DEPTH_TEST)
        
        #Enable the blending with MIP projection. You can change GL_MAX to 
        #other stuff if you want to.
        glBlendEquation(GL_MAX)		
        glEnable(GL_BLEND)
        
        #Defines shading (probably not very important here)
        glShadeModel(GL_SMOOTH)
	
	    #Size the window (often done automatically, but one time more does not kill
	    #anyone)
        self.ReSizeGLScene(Width, Height)
                   
    def DrawGLScene(self):
        #With resize, we already are in MODELVIEW mode
        
        #Clear the buffers we will write into
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        #Reinitialize all the transformations (previous are cancelled)
        glLoadIdentity()
        
        #Defines which one of the textures we are going to use
        glBindTexture(GL_TEXTURE_3D, self.textures) 

        #My object is defined by the coordinates [-1,1;-1,1;-1,1]
        #Zero is the center, and I am in orhographic projection, so no in depth
        #translation needed
        glTranslatef(0.0,0.0,0.0)
        
        #Rotate the volume
        glRotatef(self.yzrotation,1.0,0.0,0.0)
        glRotatef(self.xzrotation,0.0,1.0,0.0)
        glRotatef(self.xyrotation,0.0,0.0,1.0)
        		
                
        
        #My "cube" is defined by 6 independent faces, that I assemble like a
        #cube. Basically though, I just draw the texture on each face.
        
        glBegin(GL_QUADS)
        
        for d in np.arange(-1.,1.,1./256.):
            td = (d+1.)/2.
            glNormal3f(d,0.0,0.0)
            
            glTexCoord3f(td,1.,1.)
            glVertex3f(1.,1.,d)
            
            glTexCoord3f(td,0.,1.)
            glVertex3f(-1.,1.,d)
            
            glTexCoord3f(td,0.,0.)
            glVertex3f(-1.,-1.,d)
            
            glTexCoord3f(td,1.,0.)
            glVertex3f(1.,-1.,d)

        
        glEnd()

    def changelight(self):
        self.light = not self.light
        if(self.light):
            glEnable(GL_LIGHT1)
        else:
            glDisable(GL_LIGHT1)
            
    def changeblending(self):
        self.blending = not self.blending
        if(self.blending):
            glEnable(GL_BLEND)
        else:
            glDisable(GL_BLEND)
           
    def changedepth(self):
        self.depthtest = not self.depthtest
        if(self.depthtest):
            glEnable(GL_DEPTH_TEST)
        else:
            glDisable(GL_DEPTH_TEST)
            
    def increasexyrotation(self):
        self.xyrotation = self.xyrotation+1
        
    def decreasexyrotation(self):
        self.xyrotation = self.xyrotation-1
        
    def increaseyzrotation(self):
        self.yzrotation = self.yzrotation+1
        
    def decreaseyzrotation(self):
        self.yzrotation = self.yzrotation-1

    def increasexzrotation(self):
        self.xzrotation = self.xzrotation+1
        
    def decreasexzrotation(self):
        self.xzrotation = self.xzrotation-1	        

class GLWindow:
    def __init__(self,Width,Height,canvas):
        glutInit("")
            
        glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_ALPHA | GLUT_DEPTH)
        glutInitWindowSize(Width,Height)
        glutInitWindowPosition(0, 0)
        self.canvas = canvas
        self.window = glutCreateWindow("dicomviewer")
        glutDisplayFunc(self.DrawGLScene)
        glutIdleFunc(self.DrawGLScene)
        glutReshapeFunc(self.ReSizeGLScene)
        glutKeyboardFunc(self.keyPressed)
        glutSpecialFunc(self.specialkeypressed)
        self.bool = 0
        #glutFullScreen()
    
    def DrawGLScene(self):
        self.canvas.DrawGLScene()	    
        #  Echanger les buffers pour afficher celui dans lequel on a ecrit 
        glutSwapBuffers()
        
    def ReSizeGLScene(self,x,y):
        self.canvas.ReSizeGLScene(x,y)
        
    def keyPressed(self,key,x,y):
        key = ord(key)
        if key == ESCAPE:
            glutDestroyWindow(self.window)
            sys.exit()
        elif key== E_CHAR:
            if(self.bool == 0):
                self.bool = 1
                glutFullScreen()
        elif key == FILTER:
            self.canvas.filter = self.canvas.filter+1
            if(self.canvas.filter>2):
                self.canvas.filter = 0
        elif key == LIGHTN:
            self.canvas.changelight()
        elif key == BLENDT:
            self.canvas.changeblending()
        elif key == DEPTHT:
            self.canvas.changedepth()
    
    def specialkeypressed(self,key,x,y):
        if key == LEFTXY:
            self.canvas.decreasexyrotation()
        elif key == RIGHXY:
            self.canvas.increasexyrotation()
        elif key == DOARYZ:
            self.canvas.decreaseyzrotation()
        elif key == UPARYZ:
            self.canvas.increaseyzrotation()
        elif key == LEARXZ:
            self.canvas.decreasexzrotation()
        elif key == RIARXZ:
            self.canvas.increasexzrotation()
            
    def run(self):
        glutMainLoop()

if __name__=="__main__":	        
    cv = Canvas(argv[1])
    win = GLWindow(640,480,cv)
    cv.initGL(640,480)
    win.run()
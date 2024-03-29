from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5 import QtCore, QtGui, QtWidgets
import ctypes
from ctypes import c_void_p
import sys
sys.path.append('..')
from color_pick import ColorElement

null = c_void_p(0)

class ExampleQGLWidget(QtWidgets.QOpenGLWidget):

    def __init__(self, parent):
        QtWidgets.QOpenGLWidget.__init__(self, parent)

        #FIXME
        self.blobs = [
        ColorElement((50, 50), 100, (245, 173, 66)),
        ColorElement((75, 75), 70, (4, 5, 210)),
        ColorElement((300, 300), 100, (0, 255, 0)),
        ]
        self.blobCount = len(self.blobs)
        self.dirty = True

    def initShaders(self):
        blobArrLen = self.blobCount or 1

        uBlobStr = 'uniform vec2 uBlobPos[{}];'.format(blobArrLen)
        vBlobStr = 'varying vec2 vBlobPos[{}];'.format(blobArrLen)

        uBlobColorStr = 'uniform vec3 uBlobColor[{}];'.format(blobArrLen)
        vBlobColorStr = 'varying vec3 vBlobColor[{}];'.format(blobArrLen)

        uBlobRadiusStr = 'uniform float uBlobRadius[{}];'.format(blobArrLen)
        vBlobRadiusStr = 'varying float vBlobRadius[{}];'.format(blobArrLen)

        vertex = """
        #version 330
        in vec4 position;
        uniform float uW;
        uniform float uH;
        varying float vW;
        varying float vH;
        {}
        {}
        {}
        {}
        {}
        {}
        void main() {{
            vW = uW;
            vH = uH;
            for (int i = 0; i < {}; ++i) {{
                vBlobPos[i] = uBlobPos[i];
                vBlobColor[i] = uBlobColor[i];
                vBlobRadius[i] = uBlobRadius[i];
            }}
            gl_Position = position;
        }}
        """.format(uBlobStr, vBlobStr, uBlobColorStr, vBlobColorStr, uBlobRadiusStr, vBlobRadiusStr, self.blobCount)

        vShader = self.getShader(vertex, GL_VERTEX_SHADER)
        if not vShader:
            return

        fragment = """
        #version 330
        out vec4 outputColor;
        precision highp float;
        varying float vW;
        varying float vH;
        varying float vBlobCnt;
        {}
        {}
        {}
        void main(void) {{
            const int blobCnt = {};
            if (blobCnt == 0) {{
                gl_FragColor = vec4(1.0, 1.0, 1.0, 1.0);
                return;
            }}
            float b2 = 0.25;
            float b4 = b2 * b2;
            float b6 = b4 * b2;
            float influenceSum = 0.0;
            vec3 colors = vec3(0.0, 0.0, 0.0);
            for (int i = 0; i < blobCnt; ++i) {{
                float r = vBlobRadius[i];
                vec2 pos = vBlobPos[i];
                float dx = pos.x - float(gl_FragCoord.x);
                float dy = pos.y - float(gl_FragCoord.y);
                float d2 = (dx * dx + dy * dy) / r / r;
                if (d2 <= b2) {{
                    float d4 = d2 * d2;
                    float influence = 1.0 - (4.0 * d4 * d2 / b6 - 17.0 * d4
                        / b4 + 22.0 * d2 / b2) / 9.0;
                    if (influence < 0.001) {{
                        continue;
                    }}
                    colors = colors + vBlobColor[i] * influence;
                    //colors = colors + vec3((i%3)*.25, ((i+1)%3)*.25, ((i+2)%3)*.25) * influence;
                    influenceSum += influence;
                }}
            }}
            if (influenceSum < 0.4) {{
                outputColor = vec4(1.0, 1.0, 1.0, 1.0);
            }}
            else {{
                outputColor = vec4(colors / influenceSum, 1.0);
            }}
        }}
        """.format(vBlobStr, vBlobColorStr, vBlobRadiusStr, self.blobCount)

        fShader = self.getShader(fragment, GL_FRAGMENT_SHADER)
        if not fShader:
            return

        self.shaderProgram  = glCreateProgram()
        glAttachShader(self.shaderProgram, vShader)
        glAttachShader(self.shaderProgram, fShader)
        glLinkProgram(self.shaderProgram)

        if glGetProgramiv(self.shaderProgram, GL_LINK_STATUS) == 0:
            print('Could not link shader program')

        glUseProgram(self.shaderProgram)

    def getShader(self, text, type):
        shader = glCreateShader(type)
        glShaderSource(shader, text)
        glCompileShader(shader)

        if glGetShaderiv(shader, GL_COMPILE_STATUS) == 0:
            print('Shader could not be compiled.\n' + str(glGetShaderInfoLog(shader)))
            glDeleteShader(shader)
            return

        return shader

    def initBuffers(self):
        self.positionBuffer = glGenBuffers(1)
        positions = [-1,-1,1,-1,-1,1,1,1]
        sizeOfFloat = ctypes.sizeof(GLfloat)
        array_type = (GLfloat * len(positions))
        glBindBuffer(GL_ARRAY_BUFFER, self.positionBuffer)
        glBufferData(GL_ARRAY_BUFFER, len(positions) * sizeOfFloat,
            array_type(*positions), GL_STATIC_DRAW)

    def initBlobBuffers(self, blobs):
        blobPos = []
        blobColor = []
        blobRadius = []
        for blob in blobs:
            blobPos.append(blob.x)
            blobPos.append(blob.y)
            blobColor.append(blob.color[0] / 255.)
            blobColor.append(blob.color[1] / 255.)
            blobColor.append(blob.color[2] / 255.)
            blobRadius.append(blob.radius)

        uPos = glGetUniformLocation(self.shaderProgram, 'uBlobPos')
        if uPos != -1:
            glUniform2fv(uPos, len(blobPos), blobPos)
        uColor = glGetUniformLocation(self.shaderProgram, 'uBlobColor')
        if uColor != -1:
            glUniform3fv(uColor, len(blobColor), blobColor)
        uRadius = glGetUniformLocation(self.shaderProgram, 'uBlobRadius')
        if uRadius != -1:
            glUniform1fv(uRadius, len(blobRadius), blobRadius)


    def paintGL(self):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT)

        glUseProgram(self.shaderProgram)

        #FIXME
        # Rebuild shader when blob number changes
        # init blob buffers only (don't rebuild shader) when blob
        # color or position changes, but not the number of blobs?
        if self.dirty:
            self.blobs = self.blobs # new blobs
            self.blobCount = len(self.blobs)
            self.initShaders()
            self.initBlobBuffers(self.blobs)
            self.dirty = False

        uW = glGetUniformLocation(self.shaderProgram, 'uW')
        if uW != -1:
            glUniform1f(uW, self.width)
        uH = glGetUniformLocation(self.shaderProgram, 'uH')
        if uH != -1:
            glUniform1f(uH, self.height)


        if self.positionBuffer != -1:
            glBindBuffer(GL_ARRAY_BUFFER, self.positionBuffer)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, False, 0, null)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)


    def resizeGL(self, w, h):
        self.width = w
        self.height = h
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

    def initializeGL(self):
        glViewport(0,0, 640, 480)
        self.width, self.height = 640, 480
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClearDepth(1.0)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        self.initShaders()
        self.initBuffers()

class TestContainer(QtWidgets.QMainWindow):

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        widget = ExampleQGLWidget(self)
        self.setCentralWidget(widget)

if __name__ == '__main__':
    app = QtWidgets.QApplication(['Shader Example'])
    window = TestContainer()
    window.show()
    app.exec_()
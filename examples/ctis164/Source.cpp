// CTIS164 event-driven OpenGL/GLUT skeleton.
#include <GL/glut.h>

const int winWidth = 640;
const int winHeight = 480;
const int timerDelay = 30;

float circleX = 0.0f;
float circleY = 0.0f;
float circleRadius = 0.3f;
bool animationRunning = false;

// Convert a world-space y value into a window pixel coordinate so the
// drawing origin sits at the bottom-left of the projection.
int toScreenY(int y) {
    return winHeight / 2 - y;
}

void onDisplay() {
    // STEP #1: Clear the window to the background colour.
    glClear(GL_COLOR_BUFFER_BIT);

    // STEP #2: Draw the moving shape at the current state position.
    glColor3f(1.0f, 1.0f, 1.0f);
    glBegin(GL_QUADS);
    float half = circleRadius;
    glVertex2f(circleX - half, circleY - half);
    glVertex2f(circleX + half, circleY - half);
    glVertex2f(circleX + half, circleY + half);
    glVertex2f(circleX - half, circleY + half);
    glEnd();

    // STEP #4: Swap the back and front buffers.
    glutSwapBuffers();
}

void onTimer(int value) {
    if (value != 1) {
        return;
    }
    if (animationRunning) {
        circleY += 0.02f;
        if (circleY > 1.0f - circleRadius) {
            circleY = 1.0f - circleRadius;
            animationRunning = false;
        }
    }
    // Re-register the timer so the animation keeps advancing.
    glutTimerFunc(timerDelay, onTimer, 1);
    glutPostRedisplay();
}

void onKeyboard(unsigned char key, int x, int y) {
    (void)x;
    (void)y;
    if (key == ' ') {
        animationRunning = !animationRunning;
    }
}

void onSpecial(int key, int x, int y) {
    (void)x;
    (void)y;
    if (key == GLUT_KEY_LEFT) {
        circleX -= 0.05f;
    } else if (key == GLUT_KEY_RIGHT) {
        circleX += 0.05f;
    }
}

void onSpecialUp(int key, int x, int y) {
    (void)key;
    (void)x;
    (void)y;
    circleRadius = 0.3f;
}

void onReshape(int width, int height) {
    glViewport(0, 0, width, height);
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    gluOrtho2D(-1.0, 1.0, -1.0, 1.0);
    glMatrixMode(GL_MODELVIEW);
}

int main(int argc, char **argv) {
    glutInit(&argc, argv);
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA);
    glutInitWindowSize(winWidth, winHeight);
    glutCreateWindow("CTIS164 event-driven scene");

    glClearColor(0.0f, 0.0f, 0.2f, 1.0f);

    // STEP #3: Register the event-handler callbacks.
    glutDisplayFunc(onDisplay);
    glutReshapeFunc(onReshape);
    glutKeyboardFunc(onKeyboard);
    glutSpecialFunc(onSpecial);
    glutSpecialUpFunc(onSpecialUp);
    glutTimerFunc(timerDelay, onTimer, 1);

    // STEP #4: Start the event dispatcher.
    glutMainLoop();
    return 0;
}

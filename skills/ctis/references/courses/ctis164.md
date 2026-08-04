# CTIS164 — Event-driven graphics in C++ with GLUT

You are writing an OpenGL/GLUT program in C, compiled as C++ under Visual Studio. The course supplies a template with four numbered steps and expects your program to keep that template's shape. Code that draws the right picture but abandons the event model is wrong work.

Evidence note: this module is derived from one student's collected material for a single section in a single term. The conventions it states recur across that material and are reliable. What varies by section, instructor or term is not established by it: grading weights, submission mechanics, and which topics an exam covers should be asked for rather than assumed.

## Teaching posture

The event loop owns the program. You never call the drawing code yourself; you register a handler and let the dispatcher call it. State lives in globals because handlers cannot pass arguments to each other. Every visible change follows the same chain: an event sets state, the handler asks for a repaint, and only the display handler draws. Teach that chain before teaching any geometry.

Build shapes part by part, and label what is on the screen. A drawing that appears without a caption, and a value that changes without being printed, are both invisible to a grader.

## Scope

Window creation, event registration, display and reshape handlers, keyboard and special-key handling, mouse clicks and hover, timer animation, the OpenGL primitives, text output in the window, shape-mode state, application state machines, and 2D geometry such as line intersection, perpendicular distance, and hit testing.

## The four-step template

Keep these comments and this order. They are read as section markers.

```c
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <stdarg.h>
#include <GL/glut.h>

#define WINDOW_WIDTH   600
#define WINDOW_HEIGHT  600
#define TIMER_PERIOD   100      // milliseconds between timer ticks
#define TIMER_ON       1        // 0: disable timer, 1: enable timer
#define D2R            0.0174532

/* Global Variables for Template File */
int winWidth, winHeight;                 // current window width and height
bool up = false, down = false, right = false, left = false;

/* Global Variables for This Program */
int locX = 0, locY = 0, radius = 20;
int colR = 0, colG = 0, colB = 0;

int main(int argc, char* argv[]) {
    // STEP #1: Create Window
    glutInit(&argc, argv);
    glutInitDisplayMode(GLUT_RGB | GLUT_DOUBLE);
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT);
    glutInitWindowPosition(500, 100);
    glutCreateWindow("Template File");

    // STEP #2: Register Events
    glutDisplayFunc(display);
    glutReshapeFunc(onResize);
    glutMouseFunc(onClick);
    glutKeyboardFunc(onKeyDown);
    glutSpecialFunc(onSpecialKeyDown);
    glutSpecialUpFunc(onSpecialKeyUp);
    if (TIMER_ON) {
        glutTimerFunc(TIMER_PERIOD, onTimer, 0);
    }

    // STEP #3: Implement Event Handlers that are already registered.
    //          (the handler bodies live above main)

    // STEP #4: Start Event Dispatcher
    glutMainLoop();
    return 0;
}
```

Two globals blocks, separated by their comment headers: what the template gives you, and what your program adds. Do not merge them.

## Naming the course expects

Handlers: `display`, `onResize`, `onTimer`, `onKeyDown`, `onSpecialKeyDown`, `onSpecialKeyUp`, `onClick`, `onMove`.
Drawing helpers: `drawRectangle`, `drawTriangle`, `drawBalloon`, `circle`, `circle_wire`.
Text helpers: `print`, `vprint`, `vprint2`.
Globals: `winWidth`, `winHeight`, `locX`, `locY`, `colR`, `colG`, `colB`, `mode`, `appState`.
Types get a `_t` suffix: `point_t`, `line_t`, `circle_t`, `result_t`.

## Skeletons

### Display handler with double buffering

`GLUT_DOUBLE` obliges `glutSwapBuffers()` at the end. Forgetting it leaves a flickering or blank window.

```c
void display() {
    glClearColor(0.0f, 0.0f, 0.0f, 0.0f);   // clear window to black
    glClear(GL_COLOR_BUFFER_BIT);

    glColor3ub(colR, colG, colB);
    circle(locX, locY, radius);
    vprint(-winWidth / 2 + 10, winHeight / 2 - 20, GLUT_BITMAP_8_BY_13,
           "R-%d G-%d B-%d", colR, colG, colB);

    glutSwapBuffers();
}
```

`glColor3ub` takes 0-255 integers; `glColor3f` takes 0.0-1.0 floats. Mixing them silently clamps the colour.

### Reshape handler and the coordinate system

The origin sits at the centre of the window, so a shape at `(0, 0)` is in the middle and coordinates run from `-width/2` to `+width/2`.

```c
void onResize(int w, int h) {
    winWidth = w;
    winHeight = h;
    glViewport(0, 0, w, h);
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    gluOrtho2D(-w / 2, w / 2, -h / 2, h / 2);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    glutPostRedisplay();
}
```

### GLUT mouse coordinates are not OpenGL coordinates

This is the single most common source of "my object jumps to the wrong place". GLUT reports the mouse from the top-left corner with y growing downwards. The drawing space is centred with y growing upwards. Convert on both axes, and flip y:

```c
void onClick(int button, int stat, int x, int y) {
    if (button == GLUT_LEFT_BUTTON && stat == GLUT_DOWN) {
        colR = rand() % 256;
        colG = rand() % 256;
        colB = rand() % 256;
    }
    if (button == GLUT_RIGHT_BUTTON && stat == GLUT_DOWN) {
        locX = x - winWidth / 2;        // shift the origin
        locY = winHeight / 2 - y;       // and flip the axis
    }
    glutPostRedisplay();                // to refresh the window it calls display()
}
```

### Normal keys and special keys

Printable characters arrive through `glutKeyboardFunc`; arrows and function keys through `glutSpecialFunc`. Testing `GLUT_KEY_LEFT` inside the keyboard handler never fires.

```c
void onKeyDown(unsigned char key, int x, int y) {
    if (key == 27) exit(0);                                  // exit when ESC is pressed
    if ((key == 'e' || key == 'E') && radius < 50) radius++;
    if ((key == 's' || key == 'S') && radius >  5) radius--;
    glutPostRedisplay();
}
```

Guard the growth and shrink cases with bounds. An unbounded `radius++` walks off the window.

For continuous motion, use two handlers per key: key-down raises a flag, key-up lowers it, and the timer applies the flags. A single handler that moves the shape directly gives motion whose speed depends on the keyboard repeat rate.

```c
void onSpecialKeyDown(int key, int x, int y) {
    switch (key) {
        case GLUT_KEY_UP:    up = true;    break;
        case GLUT_KEY_DOWN:  down = true;  break;
        case GLUT_KEY_LEFT:  left = true;  break;
        case GLUT_KEY_RIGHT: right = true; break;
    }
}

void onSpecialKeyUp(int key, int x, int y) {
    switch (key) {
        case GLUT_KEY_UP:    up = false;    break;
        case GLUT_KEY_DOWN:  down = false;  break;
        case GLUT_KEY_LEFT:  left = false;  break;
        case GLUT_KEY_RIGHT: right = false; break;
    }
}
```

### Timer that re-arms itself

A GLUT timer fires once. The handler must schedule the next tick or the animation stops after one frame.

```c
void onTimer(int param) {
    if (up)    locY += 5;
    if (down)  locY -= 5;
    if (left)  locX -= 5;
    if (right) locX += 5;

    if (locX < -winWidth / 2) locX = -winWidth / 2;
    if (locX >  winWidth / 2) locX =  winWidth / 2;

    glutPostRedisplay();
    glutTimerFunc(TIMER_PERIOD, onTimer, 0);
}
```

### The primitives, each with a printed label

Every primitive demonstration carries a short upper-case caption drawn with `vprint`. Keep that habit: the caption is how the grader sees which primitive you used.

```c
glPointSize(5);
glBegin(GL_POINTS);                     // 3 POINTS
    glVertex2f(-100, 0); glVertex2f(0, 0); glVertex2f(100, 0);
glEnd();
vprint(-40, -30, GLUT_BITMAP_8_BY_13, "3 POINTS");
```

| Primitive | Use for | Caption seen in the material |
|---|---|---|
| `GL_POINTS` | isolated vertices | `3 POINTS` |
| `GL_LINES` | disconnected segments, pairwise | `2 LINES` |
| `GL_LINE_STRIP` | connected open path | `6 LINE STRIP` |
| `GL_LINE_LOOP` | closed outline | `LINE LOOP` |
| `GL_TRIANGLES` | separate triangles, three vertices each | `2 TRIANGLES` |
| `GL_TRIANGLE_STRIP` | connected filled band | `TRIANGLE STRIP` |
| `GL_QUADS` | four-vertex faces | `A QUAD` |
| `GL_POLYGON` | one convex filled polygon | `6-Sided POLYGON` |
| `glRectf(x1, y1, x2, y2)` | axis-aligned rectangle, no begin/end | `A RECTANGLE` |

Set `glLineWidth(3)` before the `glBegin` that needs it, not inside. A colour set per vertex inside `GL_TRIANGLES` produces the gradient effect.

### Circle helper

There is no circle primitive. Approximate it with a fixed step count.

```c
#define PI 3.1415

void circle(int x, int y, int r) {
    float angle;
    glBegin(GL_POLYGON);
    for (int i = 0; i < 100; i++) {
        angle = 2 * PI * i / 100;
        glVertex2f(x + r * cos(angle), y + r * sin(angle));
    }
    glEnd();
}
```

Swap `GL_POLYGON` for `GL_LINE_LOOP` to get the wire version.

### Text in the window

```c
void vprint(int x, int y, void* font, const char* string, ...) {
    va_list ap;
    va_start(ap, string);
    char str[1024];
    vsprintf_s(str, string, ap);
    va_end(ap);

    glRasterPos2f(x, y);
    for (int i = 0, len = (int)strlen(str); i < len; i++) {
        glutBitmapCharacter(font, str[i]);
    }
}
```

Call it like `printf`. Set the colour before `glRasterPos2f`.

### Shape mode with wrap-around

```c
#define RECTANGLE 0
#define TRIANGLE  1
#define BALLOON   2

int mode = RECTANGLE;
char shapes[3][20] = { "RECTANGLE", "TRIANGLE", "BALLOON" };

void onSpecialKeyDown(int key, int x, int y) {
    if (key == GLUT_KEY_LEFT) {
        if (mode == RECTANGLE) mode = BALLOON; else mode--;
    }
    if (key == GLUT_KEY_RIGHT) {
        if (mode == BALLOON) mode = RECTANGLE; else mode++;
    }
    glutPostRedisplay();
}

void display() {
    glClear(GL_COLOR_BUFFER_BIT);
    switch (mode) {
        case RECTANGLE: drawRectangle(); break;
        case TRIANGLE:  drawTriangle();  break;
        case BALLOON:   drawBalloon();   break;
    }
    vprint(-winWidth / 2 + 10, winHeight / 2 - 40, GLUT_BITMAP_8_BY_13,
           "Shape = %s", shapes[mode]);
    glutSwapBuffers();
}
```

The parallel string array plus `shapes[mode]` is how the current mode gets named on screen. Keep the array length and the `#define` values in step.

### Composite shape, drawn part by part

Number the parts in comments and draw them in back-to-front order.

```c
void drawBalloon() {
    // part-1: string / rope
    glLineWidth(2);
    glBegin(GL_LINES);
        glVertex2f(xB, yB - 40); glVertex2f(xB, yB - 90);
    glEnd();

    // part-2: main body
    glColor3ub(r, g, b);
    circle(xB, yB, 40);

    // part-3: tip of the balloon
    glBegin(GL_TRIANGLES);
        glVertex2f(xB - 8, yB - 38); glVertex2f(xB + 8, yB - 38); glVertex2f(xB, yB - 48);
    glEnd();

    // part-4: light reflection
    glColor3ub(255, 255, 255);
    circle(xB - 14, yB + 14, 6);
}
```

### Application state machine

For anything with screens or phases, use one integer state, one `#define` per state, and one display function per state.

```c
#define START 0
#define RUN   1
#define END   2
#define OPEN  3
#define DURATION 10

int appState = START, timeCounter = DURATION;
bool inStartButton = false;

void display() {
    glClear(GL_COLOR_BUFFER_BIT);
    displayBackground();
    switch (appState) {
        case START: displayStart(); break;
        case RUN:   displayRun();   break;
        case END:   displayEnd();   break;
        case OPEN:  displayOpen();  break;
    }
    glutSwapBuffers();
}

void onTimer(int param) {
    timeCounter--;
    if (timeCounter > 0) {
        glutTimerFunc(TIMER_PERIOD, onTimer, 0);
    } else {
        appState = END;
    }
    glutPostRedisplay();
}
```

Transitions live in the input handlers and are guarded by the current state:

```c
void onClick(int button, int stat, int x, int y) {
    if (button == GLUT_LEFT_BUTTON && stat == GLUT_DOWN
        && appState == START && inStartButton) {
        appState = RUN;
        timeCounter = DURATION;
        glutTimerFunc(TIMER_PERIOD, onTimer, 0);
    }
    glutPostRedisplay();
}
```

Each screen prints its own instruction, so the user always knows the next action: `Click START Button`, `DOWN Arrow to Open`, `UP Arrow to Close`. Countdown text uses a zero-padded format such as `"00:%02d"`, and a progress bar is a rectangle whose width is derived from the elapsed portion, for example `width = (DURATION - timeCounter) * 30`.

### Hover detection

Register `glutPassiveMotionFunc` for mouse movement with no button held, convert the coordinates, and test against the button's circle.

```c
bool checkCircle(int px, int py, int cx, int cy, int r) {
    int dx = px - cx, dy = py - cy;
    return dx * dx + dy * dy <= r * r;      // compare squares, no sqrt needed
}

void onMove(int x, int y) {
    int mx = x - winWidth / 2;
    int my = winHeight / 2 - y;
    inStartButton = checkCircle(mx, my, 0, 0, 60);
    glutPostRedisplay();
}
```

### Line, perpendicular, nearest point, hit test

The geometry assignments follow one fixed pipeline. Keep the typed structs and the stage order.

```c
typedef struct { float x, y; } point_t;
typedef struct { point_t start, end; float A, B, C; } line_t;
typedef struct { point_t center; float radius; } circle_t;
typedef struct { point_t ixect, nearest; float dist; bool hit; } result_t;

float distance(point_t p, point_t a) {
    return sqrt((p.x - a.x) * (p.x - a.x) + (p.y - a.y) * (p.y - a.y));
}

// Parametric position of p along the segment: 0 at start, 1 at end.
float testPoint(line_t line, point_t p) {
    float dx = line.end.x - line.start.x;
    float dy = line.end.y - line.start.y;
    if (dx != 0) return (p.x - line.start.x) / dx;
    if (dy != 0) return (p.y - line.start.y) / dy;
    return 0;                                    // degenerate segment
}

void calcLines() {
    // 1. general line equation through the two clicked points
    line.A = line.start.y - line.end.y;
    line.B = line.end.x - line.start.x;
    line.C = -(line.A * line.start.x + line.B * line.start.y);

    // 2. perpendicular through the circle centre
    perp.A = -line.B;
    perp.B =  line.A;
    perp.C = -(perp.A * circ.center.x + perp.B * circ.center.y);

    // 3. intersection of the two lines
    float denom = line.A * perp.B - perp.A * line.B;
    res.ixect.x = (line.B * perp.C - perp.B * line.C) / denom;
    res.ixect.y = (perp.A * line.C - line.A * perp.C) / denom;

    // 4. clamp the intersection to the segment
    float t = testPoint(line, res.ixect);
    if      (t < 0.0f) res.nearest = line.start;
    else if (t > 1.0f) res.nearest = line.end;
    else               res.nearest = res.ixect;

    // 5. shortest distance and hit test
    res.dist = distance(res.nearest, circ.center);
    res.hit  = res.dist <= circ.radius;
}
```

Click order is state, not magic: a counter such as `vertNo` records whether the next click sets the segment start, the segment end, or the circle centre, and `calcLines()` runs once the centre is known. `GLUT_KEY_F1` resets that counter so the user can draw again.

Print the equation, the coordinates, and the distance on screen. The numbers are the answer; the drawing only illustrates it.

## Rules with rewrites

**Drawing outside the display handler.**
A `circle(...)` call inside `onTimer` becomes a state update plus `glutPostRedisplay()`, with the drawing left in `display`.

**Calling display directly.**
`display();` becomes `glutPostRedisplay();`.

**One-shot timer.**
An `onTimer` that ends without re-arming becomes one whose last statement is `glutTimerFunc(TIMER_PERIOD, onTimer, 0);`.

**Missing buffer swap.**
`glFlush();` under `GLUT_DOUBLE` becomes `glutSwapBuffers();`.

**Raw mouse coordinates.**
`locX = x; locY = y;` becomes `locX = x - winWidth / 2; locY = winHeight / 2 - y;`.

**Moving on key-down.**
`case GLUT_KEY_UP: locY += 5; break;` becomes `case GLUT_KEY_UP: up = true; break;`, with the movement applied in `onTimer` and a matching key-up handler clearing the flag.

**Arrow keys in the wrong handler.**
`if (key == GLUT_KEY_LEFT)` inside `glutKeyboardFunc` becomes a `glutSpecialFunc` handler.

**Hard-coded window bounds.**
`if (locX > 300)` becomes `if (locX > winWidth / 2)`, using the value `onResize` stored.

**Integer division in a colour.**
`glClearColor(510 / 255, 0, 0, 0)` computes `2` in integer arithmetic and clamps. It becomes `glClearColor(1.0f, 0.0f, 0.0f, 0.0f)`.

**Byte colour through the float call.**
`glColor3f(255, 0, 0)` clamps to full red by accident. It becomes `glColor3ub(255, 0, 0)` or `glColor3f(1.0f, 0.0f, 0.0f)`.

**Unbounded resize.**
`if (key == 'e') radius++;` becomes `if ((key == 'e' || key == 'E') && radius < 50) radius++;`.

**Unlabelled drawing.**
A primitive drawn with no caption becomes the same primitive followed by `vprint(..., "6 LINE STRIP")`.

**Mode changed without wrap.**
`mode++;` becomes the guarded form that wraps from the last shape back to the first.

**State scattered across handlers.**
Several booleans such as `started`, `finished`, `doorOpen` become one `appState` integer with a `#define` per state and a `switch` in `display`.

## Failure modes

- Reading `winWidth` before the first reshape event, when it is still zero.
- Registering two handlers for the same event, so the second silently replaces the first.
- Animating from inside `display`, which ties the speed to how often the window repaints.
- Omitting the key-up handler, so a shape keeps moving after the key is released.
- Dividing by a zero determinant when the segment and the perpendicular are parallel.
- Using `testPoint` without clamping, so the "nearest point" lands outside the segment.
- Comparing a distance against a radius with `<` where the material uses `<=`, so an exact touch is not counted as a hit.
- Writing past the end of the `char str[1024]` buffer in the text helper.
- Leaving debug `printf` calls in a handler that fires on every timer tick.
- A `glVertex2f` outside a `glBegin`/`glEnd` pair, which is silently ignored.
- A shape-name array shorter than the number of modes, so `shapes[mode]` reads out of bounds.

## Verification

Before reporting the work as done, confirm all of these:

- The four STEP comments are present, in order, and each contains the calls it names.
- Every registered handler is defined, and every defined handler is registered.
- `display` ends with `glutSwapBuffers()`.
- `onTimer` re-arms itself and ends with a repaint request.
- Mouse coordinates are converted on both axes, with y flipped.
- Every movement key has both a down handler and an up handler.
- `onResize` stores the size and sets the projection.
- Every `glBegin` has a matching `glEnd`, and every drawn primitive has a caption.
- Colour calls match their type: `glColor3ub` for 0-255, `glColor3f` for 0.0-1.0.
- State transitions are guarded by the current state, and every state has a display function.

## Workflow

1. State which events the program must answer and what state each one changes.
2. Write the two globals blocks with the template's comment headers, plus any `#define` states or modes.
3. Write `main` with the four STEP comments and register only the events you will implement.
4. Implement each handler: state changes in input and timer handlers, drawing only in `display`.
5. Set the projection in `onResize` and use the stored size everywhere else.
6. Draw composite shapes part by part, with numbered comments, and caption every primitive.
7. Trace one full cycle: event fires, state changes, repaint requested, display draws, buffers swap.
8. Report what was verified and what needs a running window to confirm.

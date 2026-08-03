// CTIS164 pure geometry support: line/circle intersection with segment clipping.
#include <cmath>
#include <cstdio>

struct point_t {
    double x;
    double y;
};

struct line_t {
    point_t a;
    point_t b;
};

struct circle_t {
    point_t center;
    double radius;
};

struct result_t {
    bool hit;
    point_t point;
};

double distance(const point_t &p, const point_t &q) {
    double dx = p.x - q.x;
    double dy = p.y - q.y;
    return std::sqrt(dx * dx + dy * dy);
}

// Clip the perpendicular foot to the segment by its parameter t along a->b.
// t < 0 or t > 1 means the foot lies beyond an endpoint, so no segment hit.
bool testPoint(const line_t &seg, const circle_t &c, const point_t &foot, point_t &out) {
    point_t d = {seg.b.x - seg.a.x, seg.b.y - seg.a.y};
    double denom = d.x * d.x + d.y * d.y;
    if (denom == 0.0) {
        return false;
    }
    double t = ((foot.x - seg.a.x) * d.x + (foot.y - seg.a.y) * d.y) / denom;
    if (t < 0.0 || t > 1.0) {
        return false;
    }
    out.x = seg.a.x + t * d.x;
    out.y = seg.a.y + t * d.y;
    return distance(out, c.center) <= c.radius;
}

// General line equation Ax + By + C = 0 through the two segment endpoints,
// then the perpendicular from the circle center onto that line.
result_t intersect(const line_t &seg, const circle_t &c) {
    result_t res = {false, {0.0, 0.0}};
    double A = seg.a.y - seg.b.y;
    double B = seg.b.x - seg.a.x;
    double C = seg.a.x * seg.b.y - seg.b.x * seg.a.y;
    double denom = A * A + B * B;
    if (denom == 0.0) {
        return res;
    }
    double val = A * c.center.x + B * c.center.y + C;
    point_t foot = {c.center.x - A * val / denom, c.center.y - B * val / denom};
    res.hit = testPoint(seg, c, foot, res.point);
    return res;
}

int main() {
    line_t horizontal = {{0.0, 0.0}, {10.0, 0.0}};
    circle_t crossing = {{5.0, 0.0}, 1.0};
    if (!intersect(horizontal, crossing).hit) {
        return 1;
    }

    circle_t above = {{5.0, 3.0}, 1.0};
    if (intersect(horizontal, above).hit) {
        return 1;
    }

    circle_t beyond = {{15.0, 0.0}, 1.0};
    if (intersect(horizontal, beyond).hit) {
        return 1;
    }

    line_t vertical = {{5.0, -5.0}, {5.0, 5.0}};
    if (!intersect(vertical, above).hit) {
        return 1;
    }

    std::printf("GEOMETRY_OK\n");
    return 0;
}

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return str(self.x) + " " + str(self.y)

    def __eq__(self, other):
        if isinstance(other, Point):
            return self.x == other.x and self.y == other.y
        return False


class Polygon:
    def __init__(self, points):
        new_points = []
        try:
            for point in points:
                new_points.append(Point(point['longitude'], point['latitude']))
        except TypeError:
            new_points = points
        self.points = new_points

    def __str__(self):
        return "----" + "\n".join([str(point.x) + " " + str(point.y) for point in self.points])

    def is_valid(self):
        if len(self.points) < 3:
            return False
        if len(self.points) != 3:
            for i in range(len(self.points) - 2):
                for j in range(i + 2, len(self.points)):
                    if j + 1 == len(self.points):
                        if i != 0:
                            if do_lines_intersect(self.points[i], self.points[i + 1], self.points[j], self.points[0]):
                                return False
                    else:
                        if do_lines_intersect(self.points[i], self.points[i + 1], self.points[j], self.points[j + 1]):
                            return False

        if not points_on_line(self):
            return True
        return False


def points_on_line(polygon):
    for i in range(len(polygon.points) - 2):
        p1, p2, p3 = polygon.points[i], polygon.points[i + 1], polygon.points[i + 2]
        cross_product = (p2.x - p1.x) * (p3.y - p2.y) - (p2.y - p1.y) * (p3.x - p2.x)
        if cross_product != 0:
            return False
    return True


def do_lines_intersect(p1, q1, p2, q2):
    def ccw(A, B, C):
        return (C.y - A.y) * (B.x - A.x) >= (B.y - A.y) * (C.x - A.x)

    return ccw(p1, q1, p2) != ccw(p1, q1, q2) and ccw(p2, q2, p1) != ccw(p2, q2, q1)


def does_interact_with_old(polygons, new_polygon):
    for polygon in polygons:
        for i in range(len(polygon.points) - 1):
            for j in range(len(new_polygon.points) - 1):
                if do_lines_intersect(polygon.points[i], polygon.points[i + 1], new_polygon.points[j],
                                      new_polygon.points[j + 1]):
                    return True
    return False


def is_inside_old(polygons, new_polygon):
    for polygon in polygons:
        inside_points = 0
        for point in new_polygon.points:
            if is_point_inside_polygon(point, polygon):
                inside_points += 1
        if inside_points == len(new_polygon.points):
            return True
    return False


def is_inside_new(polygons, new_polygon):
    for polygon in polygons:
        inside_points = 0
        for point in polygon.points:
            if is_point_inside_polygon(point, new_polygon):
                inside_points += 1
        if inside_points == len(polygon.points):
            return True
    return False


def is_point_on_line(point, line):
    x, y = point
    (x1, y1), (x2, y2) = line
    return (min(x1, x2) <= x <= max(x1, x2) and
            min(y1, y2) <= y <= max(y1, y2) and
            abs((x2 - x1) * (y - y1) - (x - x1) * (y2 - y1)) < 1e-6)


def is_point_inside_polygon(point, polygon):
    x = point.x
    y = point.y
    inside = False
    for i in range(len(polygon.points)):
        xi = polygon.points[i].x
        yi = polygon.points[i].y
        if i + 1 == len(polygon.points):
            xj = polygon.points[0].x
            yj = polygon.points[0].y
        else:
            xj = polygon.points[i + 1].x
            yj = polygon.points[i + 1].y
        if is_point_on_line((x, y), ((xi, yi), (xj, yj))):
            return True
        intersect = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi)
        if intersect:
            inside = not inside
    return inside


def is_identical_to_old(polygons, new_polygon):
    for polygon in polygons:
        try:
            if len(polygon.points) == len(new_polygon.points):
                fin = new_polygon.points.index(polygon.points[0])
                new_poly = Polygon(new_polygon.points[fin::] + new_polygon.points[0:fin])
                if all([p1 == p2 for p1, p2 in zip(polygon.points, new_poly.points)]):
                    return True
        except ValueError:
            return False
    return False

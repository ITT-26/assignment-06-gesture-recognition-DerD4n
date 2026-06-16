import math

class Point:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

class Template:
    def __init__(self, name, points):
        self.name = name
        self.points = points

class DollarRecognizer: # generated some extra stuff for better integration later and the visualiser
    NUM_POINTS = 64
    SQUARE_SIZE = 250.0
    ANGLE_RANGE = math.radians(45)
    ANGLE_PRECISION = math.radians(2)
    PHI = 0.5 * (-1.0 + math.sqrt(5.0))

    def __init__(self, load_defaults=True): # used later to disable default templates
        self.templates = []
        if load_defaults:
            self._load_default_templates()

    def _load_default_templates(self):
        def rect():
            return [Point(0,0), Point(200,0), Point(200,100), Point(0,100), Point(0,0)]

        def square():
            return [Point(0,0), Point(100,0), Point(100,100), Point(0,100), Point(0,0)]

        def circle():
            return [
                Point(100*math.cos(t), 100*math.sin(t))
                for t in [2*math.pi*i/60 for i in range(60)]
            ]

        def check():
            return [Point(0,50), Point(50,0), Point(120,120)]

        def delete():
            return [Point(0,0), Point(120,120), Point(0,120), Point(120,0)]

        def pigtail(): # soo ai generated :)
            points = []
            num_points = 110  # Plentiful sample headroom for smooth integration
            
            # We use a parametric loop with a sweeping cubic curve baseline 
            # to maintain fluid vector trajectories across the entry, loop, and exit.
            for i in range(num_points):
                t = i / (num_points - 1)
                
                # Smooth horizontal progression from left to right
                x = t * 220.0
                
                # 1. Base sweeping wave across the bottom
                base_y = 30.0 + (1.0 - t) * 40.0 - math.sin(t * math.pi) * 20.0
                
                # 2. Add a clean, continuous loop pulse right in the middle zone
                loop_y = 0.0
                if 0.25 <= t <= 0.85:
                    # Scale t to a full circle rotation mapping (0 to 2pi)
                    loop_t = (t - 0.25) / 0.60
                    angle = loop_t * 2.0 * math.pi
                    
                    # Continuous coordinate offsets—no hard breaks or sharp edges
                    x += math.sin(angle) * 45.0
                    loop_y = (1.0 - math.cos(angle)) * 75.0
                    
                y = base_y + loop_y
                points.append(Point(x, y))
                
            return points

        for n, f in [
            ("rect", rect),
            ("square", square),
            ("circle", circle),
            ("check", check),
            ("delete", delete),
            ("pigtail", pigtail),
        ]:
            self.add_template(n, f())

    # ----------------------------
    # API
    # ----------------------------

    def add_template(self, name, points):
        self.templates.append(
            Template(name, self.normalize(points))
        )

    def recognize(self, points):
        if len(points) < 2:
            return None, 0.0, None, None

        points = self.normalize(points)

        best_name = None
        best_dist = float("inf")
        best_angle = 0.0
        best_template_pts = None

        for t in self.templates:
            # Modified to grab the optimal matching angle along with the distance
            d, angle = self.distance_at_best_angle(
                points,
                t.points,
                -self.ANGLE_RANGE,
                self.ANGLE_RANGE,
                self.ANGLE_PRECISION
            )
            if d < best_dist:
                best_dist = d
                best_name = t.name
                best_angle = angle
                best_template_pts = t.points

        half_diag = 0.5 * math.sqrt(2 * self.SQUARE_SIZE ** 2)
        score = 1.0 - best_dist / half_diag

        # Align the normalized input points using the best discovered angle
        aligned_input = self.rotate_by(points, best_angle) if best_name else None

        return best_name, max(0.0, score), aligned_input, best_template_pts

    # ----------------------------
    # Pipeline
    # ----------------------------

    def normalize(self, points):
        pts = self.resample(points, self.NUM_POINTS)
        angle = self.indicative_angle(pts)
        pts = self.rotate_by(pts, -angle)
        pts = self.scale_to_square(pts, self.SQUARE_SIZE)
        pts = self.translate_to_origin(pts)
        return pts

    def get_processing_steps(self, points):
        raw = [Point(p.x, p.y) for p in points]
        resampled = self.resample(points, self.NUM_POINTS)

        angle = self.indicative_angle(resampled)
        rotated = self.rotate_by(resampled, -angle)

        scaled = self.scale_to_square(rotated, self.SQUARE_SIZE)
        translated = self.translate_to_origin(scaled)

        return {
            "raw": raw,
            "resampled": resampled,
            "rotated": rotated,
            "scaled": scaled,
            "translated": translated
        }

    # ----------------------------
    # Steps
    # ----------------------------

    def resample(self, points, n):
        I = self.path_length(points) / (n - 1)
        D = 0.0

        pts = points[:]
        new_points = [Point(pts[0].x, pts[0].y)]

        i = 1
        while i < len(pts):
            d = self.distance(pts[i - 1], pts[i])

            if d == 0:
                i += 1
                continue

            if (D + d) >= I:
                qx = pts[i - 1].x + ((I - D) / d) * (pts[i].x - pts[i - 1].x)
                qy = pts[i - 1].y + ((I - D) / d) * (pts[i].y - pts[i - 1].y)

                q = Point(qx, qy)
                new_points.append(q)
                pts.insert(i, q)
                D = 0
            else:
                D += d

            i += 1

        if len(new_points) == n - 1:
            new_points.append(Point(points[-1].x, points[-1].y))

        return new_points

    def indicative_angle(self, points):
        c = self.centroid(points)
        return math.atan2(c.y - points[0].y, c.x - points[0].x)

    def rotate_by(self, points, angle):
        c = self.centroid(points)
        cos_a, sin_a = math.cos(angle), math.sin(angle)

        out = []
        for p in points:
            out.append(Point(
                (p.x - c.x) * cos_a - (p.y - c.y) * sin_a + c.x,
                (p.x - c.x) * sin_a + (p.y - c.y) * cos_a + c.y
            ))
        return out

    def scale_to_square(self, points, size):
        min_x = min(p.x for p in points)
        max_x = max(p.x for p in points)
        min_y = min(p.y for p in points)
        max_y = max(p.y for p in points)

        w = max_x - min_x
        h = max_y - min_y

        return [
            Point(
                p.x * (size / w if w else 1),
                p.y * (size / h if h else 1)
            )
            for p in points
        ]

    def translate_to_origin(self, points):
        c = self.centroid(points)
        return [Point(p.x - c.x, p.y - c.y) for p in points]

    # ----------------------------
    # Matching
    # ----------------------------

    def distance_at_best_angle(self, points, template, a, b, threshold):
        x1 = self.PHI * a + (1 - self.PHI) * b
        f1 = self.distance_at_angle(points, template, x1)

        x2 = (1 - self.PHI) * a + self.PHI * b
        f2 = self.distance_at_angle(points, template, x2)

        while abs(b - a) > threshold:
            if f1 < f2:
                b, x2, f2 = x2, x1, f1
                x1 = self.PHI * a + (1 - self.PHI) * b
                f1 = self.distance_at_angle(points, template, x1)
            else:
                a, x1, f1 = x1, x2, f2
                x2 = (1 - self.PHI) * a + self.PHI * b
                f2 = self.distance_at_angle(points, template, x2)

        # Return both the distance and the optimized golden angle
        if f1 < f2:
            return f1, x1
        else:
            return f2, x2

    def distance_at_angle(self, points, template, angle):
        pts = self.rotate_by(points, angle)
        return self.path_distance(pts, template)

    def path_distance(self, a, b):
        return sum(self.distance(p1, p2) for p1, p2 in zip(a, b)) / len(a)

    # ----------------------------
    # Helpers
    # ----------------------------

    def centroid(self, points):
        return Point(
            sum(p.x for p in points) / len(points),
            sum(p.y for p in points) / len(points)
        )

    def path_length(self, points):
        return sum(
            self.distance(points[i - 1], points[i])
            for i in range(1, len(points))
        )

    def distance(self, p1, p2):
        return math.hypot(p2.x - p1.x, p2.y - p1.y)
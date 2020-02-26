from scene import Scene, Node, ShapeNode, LabelNode, Size, Point, Action as A, run
import ui
import sound
import random
import math

"""
todo: increase magnification level
separate playfield node that would be scaled independntly from the starfield and text overlays
"""

MAX_EXTENT = 2000
""" ui.Path coordinates greater than 2047 cause exceptions """

BACKGROUND = (0.20, 0.20, 0.20, 1.0)


def make_path(points, line_width=1.0):
    path = ui.Path()
    path.line_cap_style = ui.LINE_CAP_ROUND
    path.line_join_style = ui.LINE_JOIN_ROUND
    path.line_width = line_width
    
    move = True
    for p in points:
        if p:
            x, y = p
            if x > 2047:
                raise ValueError(p)

            if move:
                path.move_to(x, -y)
                move = False    
            else:
                path.line_to(x, -y)
        else:
            move = True

    return path


class Particle:
    '''Physics for partical motion in 2D space'''

    def __init__(self):
        self.m = 0
        self.r = 0
        self.x = 0
        self.y = 0
        self.ar = 0.0
        self.vr = 0.0
        self.ax = 0.0
        self.ay = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.fr = 0.99
        self.gx = 0.0
        self.gy = -0.025

    def update(self, dt):
        self.vr = self.vr * self.fr + self.ar
        self.r += self.vr

        self.vx = self.vx * 0.999 + self.ax + self.gx
        self.vy = self.vy * 0.999 + self.ay + self.gy
        self.x += self.vx
        self.y += self.vy

    def null(self):
        self.r = 0
        self.vr = 0
        self.vx = 0
        self.vy = 0
        
    @property
    def a(self):
        return abs(Point(self.ax, self.ay))
        
    @a.setter
    def a(self, a):
        self.ax = -math.sin(self.r) * a
        self.ay = math.cos(self.r) * a


class Part(ShapeNode, Particle):
    def __init__(self, points):
        self.points = points
        path = make_path(points)
        path.line_width = 1.5

        ShapeNode.__init__(self, path=path, fill_color='clear', stroke_color='#bbb')
        Particle.__init__(self)


class Sound(Node):
    def __init__(self, sound):
        super().__init__()
        self.sound = sound
        self.effect = None
        self.state = 'stop'

    def play(self, volume):
        if self.state == 'stop':
            self.effect = sound.play_effect(self.sound, looping=True, volume=volume)
            self.state = 'play'
        else:
            self.set_volume(volume)

    def set_volume(self, vol):
        self.effect.volume = vol

    def ramp(self, node, progress):
        self.set_volume(self.ramp_start * (1.0 - progress))
    
    def done(self):
        self.state = 'stop'
        self.effect.stop()
        self.effect = None

    def stop(self):
        if self.state == 'play' and self.effect:
            self.ramp_start = self.effect.volume
            self.run_action(A.sequence(A.call(self.ramp, 0.2), A.call(self.done)))
            self.state = 'stopping'


class Starfield(Node):
    """ background stars """

    def __init__(self, size, count):
        Node.__init__(self)
        self.size = size
        self.add_stars(count)
        #print(self.anchor_point)
    
    def add_stars(self, count):
        path = self.star_path()
        for _ in range(count):
            x, y = random.uniform(0, self.size.w), random.uniform(0, self.size.h)
            star = ShapeNode(path=path, position=(x, y), fill_color='#fff', stroke_color='#fff')
            star.run_action(
                A.repeat(
                    A.sequence(
                        A.wait(random.uniform(2, 20)),
                        A.fade_to(0.50, 1),
                        A.fade_to(0.75, 1)
                    ), 0
                )
            )
            self.add_child(star)
                
    def star_path(self):
        path = ui.Path()
        path.move_to(0, 0)
        path.add_arc(1, 1, 3, 2, 3)
        path.line_width = 0.1
        
        return path

        
class Ship(ShapeNode, Particle):
    '''Player's ship'''
    
    MAX_THRUST = 5

    def __init__(self):
        ShapeNode.__init__(self, path=self.ship_path(), fill_color=BACKGROUND, stroke_color='#bbb')
        Particle.__init__(self)
        
        self.no_flame = ui.Path()
        self.flame = ShapeNode(path=self.no_flame, fill_color=(0, 0.0, 1.0, 0.4), stroke_color=(0, 1.0, 1.0, 0.5), parent=self)
        self.ljet = ShapeNode(path=self.no_flame, fill_color=(0, 0, 1.0, 0.1), stroke_color=(0, 1.0, 1.0, 0.5), parent=self)
        self.rjet = ShapeNode(path=self.no_flame, fill_color=(0, 0, 1.0, 0.1), stroke_color=(0, 1.0, 1.0, 0.5), parent=self)
        
        self.maxalt = 0
        self.fuel = 5000
        self.mass = 1000
        self.thrust = 0
        self.thrust_ramp = 0
        self.thrust_sound = Sound('thrust.mp3')
        self.add_child(self.thrust_sound)
            
    def update(self, dt):
        if self.thrust_ramp:
            self.set_thrust(max(self.thrust - self.thrust_ramp, 0))
            self.thrust_ramp = min(self.thrust_ramp, self.thrust)

        dfuel = self.thrust * 10 * dt
        if self.fuel < dfuel:
            self.set_thrust(self.fuel / (10 * dt))
            self.fuel = 0
        else:
            self.fuel -= dfuel

        self.a = self.thrust * 50 / (self.mass + self.fuel)

        self.maxalt = max(self.maxalt, self.y)

        self.flame.scale = random.uniform(0.99, 1.02)
        Particle.update(self, dt)
        
    def set_thrust(self, level):
        if self.fuel <= 0:
            level = 0

        self.thrust = min(level, self.MAX_THRUST)
    
        self.flame.path = self.flame_path(self.thrust)
        self.flame.position = (0, (-30 - self.flame.path.bounds.h) / 2)
        
        if level > 0.0:
            self.thrust_sound.play(self.thrust / self.MAX_THRUST)
        else:
            self.thrust_sound.stop()

    def crash(self):
        self.thrust_sound.stop()
        sound.play_effect('explosion_large_distant.mp3')
        self.fuel = max(self.fuel - 50, 0)

        # create ship parts
        prevx, prevy = self.points[0]
        for x, y in self.points[1:]:
            p = Part([(prevx, prevy), Point(x, y)])
            p.x, p.y, p.r = self.x + (x + prevx) / 2, self.y + (y + prevy) / 2, self.r
            
            prevx, prevy = x, y
            
            p.vr = random.uniform(-0.3, 0.3)
            p.vx = self.vx + random.uniform(-1, 1)
            p.vy = self.vy * -0.3 + 1
            p.run_action(A.sequence(A.fade_to(0.25, 30), A.remove()))

            self.parent.add_child(p)

    def rotate(self, level):
        #force =
        self.ar = max(min(-level / 1600, 0.01), -0.01)

        tail = self.ar * 10000
        
        path = make_path([(0, 0), (tail, 0)], 2)
                        
        if tail > 1:
            self.ljet.position = (5 + tail / 2, 10)
            self.ljet.path = path
            self.rjet.path = self.no_flame
        elif tail < -1:
            self.rjet.position = (-5 + tail / 2, 10)
            self.rjet.path = path
            self.ljet.path = self.no_flame
        else:
            self.rjet.path = self.no_flame
            self.ljet.path = self.no_flame

    def ship_path(self):
        self.points = [(-10, -15), (0, 15), (10, -15), (0, -10), (-10, -15)]
        return make_path(self.points, 1.5)
        
    def flame_path(self, level):
        if level > 0:
            tail = level * 40
        
            return make_path([(0, 0), (5, -tail), (10, 0), (5, -3), (0, 0)], 1.25)
        else:
            return ui.Path()
        
        
class Mountain(Node):
    
    def __init__(self, size):
        Node.__init__(self)
        self.anchor_point = (0, 0)
        
        self.generate_mountain(size)
        self.generate_shapes()
    
    def generate_mountain(self, size):
        self.points = [Point(0, 0), Point(20, 20)]
        x, y = 10, 10
        while x < size.w:
            dx = random.uniform(40, 80)
            if random.uniform(0, 1) < 0.6:
                dy = random.uniform(-size.h, size.h)
            else:
                dy = 0
            x = min(x + dx, size.w)
            y = max(y + dy, 20)
            y = min(y, MAX_EXTENT)

            self.points.append(Point(x, y))

    def generate_shapes(self):
        start_i = 0
        end = self.points[-1]
        for i, p in enumerate(self.points):
            start_x = self.points[start_i].x
            width = p.x - start_x
            # shapes cant be larger than 2048 wide so create multiple ShapeNodes
            if width > MAX_EXTENT or p == end:
                # get a sublist of points adjusted for the start of the panel
                points = [p - Point(start_x, 0) for p in self.points[start_i:i]]
                base = [Point(points[-1].x, 0), Point(0, 0), Point(0, points[0].y)]
                
                path = make_path(points + base, 1.5)
                panel = ShapeNode(path=path, fill_color=BACKGROUND, stroke_color='clear')
                panel.anchor_point = (0, 0)
                panel.position = (start_x, 0)
                self.add_child(panel)
                
                path = make_path(points, 1.5)
                path.move_to(0, 0)
                path.line_to(0, 0)
                panel = ShapeNode(path=path, fill_color='clear', stroke_color='#bbb')
                panel.anchor_point = (0, 0)
                panel.position = (start_x, 0)
                self.add_child(panel)

                start_i = i - 1
    
    def get_points(self, x):
        if x >= 0:
            pp = self.points[0]
            for p in self.points[1:]:
                if x < p.x:
                    return pp, p
                pp = p

        return None, None
             
    def get_y(self, x):
        pp, p = self.get_points(x)
        if pp and p:
            slope = (p.y - pp.y) / (p.x - pp.x)
            return pp.y + slope * (x - pp.x)
  
        return 0

    def is_level(self, x1, x2):
        if x1 > 0 and x2 > 0:
            pp = Point(0, 0)
            for p in self.points:
                if x1 > pp.x and x2 > pp.x and x1 < p.x and x2 < p.x:
                    if pp.y == p.y:
                        return True
                    else:
                        return False
                pp = p
        return False

    def is_above_ground(self, particle, dy):
        ground_level = self.get_y(particle.x) + dy
        return particle.y > ground_level


class MyScene(Scene):
    def setup(self):
        print('setup')
        self.paused = True
        self.running = False
        self.landings = []
        self.crashes = 0
        self.left_touch = None
        self.right_touch = None

        self.background_color = BACKGROUND
        
        self.playfield = Node(parent=self)
        print(self.playfield.position)

        self.ship = Ship()
        self.ship.z_position = 1
        self.playfield.add_child(self.ship)

        width = 30_000
        self.mt = Mountain(Size(width, 300))
        self.mt.z_position = 0
        self.playfield.add_child(self.mt)

        self.stars = Starfield(self.size, 200)
        
        self.stars.z_position = -1
        self.add_child(self.stars)
        
        self.label = LabelNode(text='', font=('Menlo', 20), parent=self)
        self.label.position = (self.size.w / 2, self.size.h - 20)
        
        self.stats = LabelNode(text='stats', font=('Menlo', 16), parent=self)
        self.stats.position = (self.size.w / 2, self.size.h - 40)
        self.stats.z_position = 5
        
        self.update_scale()
        self.reset()
        
    def did_change_size(self):
        pass
    
    def update(self):
        if self.running:
            self.ship.update(self.dt)

            # adjusted gl.  20 is approx ship radius
            adj = 17

            if self.landed:
                if self.mt.is_above_ground(self.ship, adj):
                    self.landed = False
                else:
                    self.ship.y = self.mt.get_y(self.ship.x) + adj
                    self.ship.null()
            else:
                level = self.mt.is_level(self.ship.x - 10, self.ship.x + 10)
                hot = abs(self.ship.vy) > 1.0 or abs(self.ship.vx) > 0.30 or not level

                self.label.text = f'vx:{self.ship.vx:+4.2f} vy:{self.ship.vy:+4.2f} r:{self.ship.r:4.2f} l:{level}'
                self.label.color = '#f44' if hot else 'white'

                if not self.mt.is_above_ground(self.ship, adj) and self.ship.vy < 0:
                    if hot:
                        self.crash()
                    else:
                        self.land()
                    self.ship.y = self.mt.get_y(self.ship.x) + adj

        # recompute scale and update positions of all children
        self.update_scale()
     
        print(self.playfield.bbox)
        for c in self.playfield.children:
            if isinstance(c, Part):
                c.update(self.dt)
                if not self.mt.is_above_ground(c, 0):
                    c.y = self.mt.get_y(c.x)
                    c.vr = 0
                    c.vx = -c.vx / 2

                # viewport is centered on ship so just adjust for that
                c.position = (self.size.w / self.scale / 2 + c.x - self.ship.x, c.y)
                c.rotation = c.r
            
        self.ship.position = Point(self.size.w / 2, self.ship.y)
        #self.ship.position = Point(self.ship.x, self.ship.y)
        self.ship.rotation = self.ship.r
        
        # maintain these nodes in the same size and scale
        self.mt.position = Point(self.size.w / self.scale / 2, 0)
        #self.mt.playfield = Point(self.size.w / self.scale / 2 + 0 - self.ship.x, 0)
        #self.stars.scale = 1 / self.scale

        self.update_status()

    def update_scale(self):
        ship_ceiling = 0.75
        if self.ship.y > self.size.h * ship_ceiling:
            value = self.size.h * ship_ceiling / abs(self.ship.y) + 0.01
        else:
            value = 1

        self.playfield.scale = abs(value)

    def update_status(self):
        landings = len([x for x in self.landings if x[3] == 'land'])
        self.stats.text = 'f: {:4.0f}  pos: {:+4.0f},{:4.0f}  a: {:4.2f}  r: {:+5.3f} ar: {:+5.3f} vr: {:+5.3f}  c/l: {}/{:}'.format(
            self.ship.fuel, self.ship.x, self.ship.y, self.ship.a * 10, self.ship.r, self.ship.ar * 1000, self.ship.vr * 1000, self.crashes, landings)

    def touch_began(self, touch):
        if self.running:
            if touch.location.x < self.size.x / 2:
                self.left_touch = touch
            else:
                self.right_touch = touch
        else:
            self.left_touch = self.right_touch = None
            self.reset()

    def touch_moved(self, touch):
        if self.running:
            self.thrust_ramp = 0
            if self.left_touch and touch.location.x < self.size.x / 2:
                dist = touch.location.x - self.left_touch.location.x
                if not self.landed and abs(dist) > 20:
                    self.ship.rotate(dist / 80)
                else:
                    self.ship.rotate(0.0)
            elif self.right_touch:
                dist = -touch.location.y + self.right_touch.location.y
                self.ship.set_thrust(max((dist - 5) / 10, 0))

    def touch_ended(self, touch):
        if touch.location.x < self.size.x / 2:
            self.ship.rotate(0)
        else:
            self.ship.thrust_ramp = 0.5

    def controller_changed(self, id, key, value):
        if key == 'thumbstick_left':
            self.ship.rotate(value[0])
        elif key == 'trigger_right':
            self.ship.set_thrust(value * 4)
        elif key == 'button_b' and value:
            self.fire()
        elif key == 'button_x' and value:
            self.reset()
        elif key == 'button_y' and value:
            self.ship.fuel += 100

    def fire(self):
        path = make_path([(0, 0), (0, 1)])
        path.line_width = 2
        bullet = ShapeNode(path=path, fill_color='clear', stroke_color='white', parent=self)

        r = self.ship.rotation
        cannon = Point(math.cos(r), math.sin(r)) * 20
        bullet.position = self.ship.position + cannon
        end = bullet.position + Point(math.cos(r), math.sin(r)) * 350

        bullet.run_action(A.sequence(A.move_to(end.x, end.y, 1.5), A.remove()))
        
        sound.play_effect('fire.mp3', looping=False, volume=0.0)

    def drop_ship(self, length):
        while True:
            x = random.uniform(length / 8, length * 7 / 8)
            if self.mt.is_level(x - 10, x + 10):
                break

        lh, rh = self.mt.get_points(x)
        self.landings.append((self.t, lh, rh, 'drop'))
        self.landed = True
        self.ship.x = x
        self.ship.y = self.mt.get_y(x)
        self.ship.alpha = 1

        print('dropped:', lh, rh, self.ship.x, self.ship.y, self.ship.r)

    def crash(self):
        print('crash', self.ship.vx, self.ship.vy)

        self.ship.crash()
        self.ship.alpha = 0.0

        self.running = False
        self.crashes += 1

    def land(self):
        self.landed = True
        # only give credit for a real flight
        if self.ship.maxalt - self.ship.y > 20:
            self.ship.maxalt = self.ship.y

            lh, rh = self.mt.get_points(self.ship.x)
            
            # only give credit for the first landing
            if not  [x for x in self.landings
                     if x[1] == lh and x[2] == rh and x[3] == 'land']:
                self.landings.append((self.t, lh, rh, 'land'))
                
            print('landed', lh, rh, self.ship.x)

    def reset(self):
        self.ship.null()
        self.drop_ship(5000)
        self.label.text = ''
        self.running = True
        self.paused = False
    

if __name__ == '__main__':
    sound.stop_all_effects()
    run(MyScene(), show_fps=True)

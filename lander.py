from scene import *
import ui
import sound
import random
import math
A = Action


def make_path(points):
    path = ui.Path()
    path.line_cap_style = ui.LINE_CAP_ROUND
    path.line_join_style = ui.LINE_JOIN_ROUND

    move = True
    for p in points:
        if p:
            x, y = p
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
        
        # map to node
        self.rotation = self.r

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
        self.set_volume(1.0 - progress)
    
    def done(self):
        self.state = 'stop'
        self.effect.stop()
        self.effect = None

    def stop(self):
        if self.state == 'play' and self.effect:
            self.run_action(A.sequence(A.call(self.ramp, 0.5), A.call(self.done)))
            self.state = 'stopping'
 

class Ship(ShapeNode, Particle):
    '''Player's ship'''
    
    MAX_THRUST = 4.0

    def __init__(self):
        ShapeNode.__init__(self, path=self.ship_path(), fill_color='clear', stroke_color='#bbb')
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
            
            p.vr = random.uniform(-0.2, 0.2)
            p.vx = self.vx + random.uniform(-1, 1)
            p.vy = random.uniform(0, 3)
            p.run_action(A.sequence(A.fade_to(0.50, 5), A.remove()))

            self.parent.add_child(p)

    def rotate(self, level):
        #force =
        self.ar = max(min(-level / 1500, 0.01), -0.01)

        tail = self.ar * 10000
        
        path = make_path([(0, 0), (tail, 0)])
        path.line_width = 2
                        
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
        self.points = [(-10, -15), (0, 15), (10,-15), (0, -10), (-10, -15)]
        path = make_path(self.points)
        path.line_width = 1.5

        return path
        
    def flame_path(self, level):
        if level > 0:
            tail = level * 40
        
            path = make_path([(0, 0), (5, -tail), (10, 0), (5, -3), (0, 0)])
            path.line_width = 1.25

            return path
        else:
            return ui.Path()
        
        
class Mountain:
    def __init__(self, size):
        self.points = [Point(0, 0), Point(10, 10)]
        x, y = 10, 10
        while x < size.w:
            dx = random.uniform(50, 100)
            if random.uniform(0, 1) < 0.5:
                dy = random.uniform(-size.h, size.h)
            else:
                dy = 0
            x = min(x + dx, size.w)
            y = max(y + dy, 10)
            self.points.append(Point(x, y))
        
    def gen_path(self, scale):
        """ scale points and make path """

        path = make_path([(x * scale, y * scale) for x, y in self.points])
        path.line_width = 1.0

        return path
        
    def get_y(self, x):
        if x >= 0:
            pp = Point(0, 0)
            for p in self.points:
                if x < p.x:
                    slope = (p.y - pp.y) / (p.x - pp.x)
                    return pp.y + slope * (x - pp.x)
                pp = p
            
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
        self.landings = 0

        self.ship = Ship()
        self.ship.z_position = 1
        self.add_child(self.ship)

        self.mtdata = Mountain(Size(5000, 300))
        path = self.mtdata.gen_path(1/3)

        self.mt = ShapeNode(path=path, fill_color=self.background_color, stroke_color='#bbb')
        self.mt.scale = 3
        self.mt.anchor_point = (0, 0)
        self.z_position = 0
        self.add_child(self.mt)

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
        for c in self.children:
            if isinstance(c, Part):
                c.update(self.dt)
                if not self.mtdata.is_above_ground(c, 0):
                    c.y = self.mtdata.get_y(c.x)
                    c.vr = 0
                    c.vx = -c.vx / 2

                # viewport is centered on ship so adjust for that
                c.position = ((self.size.x / self.scale / 2) + c.x - self.ship.x, c.y)
                    
        if self.running:
            self.ship.update(self.dt)

            # adjusted gl.  20 is approx ship radius
            adj = 20

            if self.landed:
                if self.mtdata.is_above_ground(self.ship, adj):
                    self.landed = False
                    self.label.text = ''
                else:
                    self.ship.y = self.mtdata.get_y(self.ship.x) + adj
                    self.ship.null()
            else:
                level = self.mtdata.is_level(self.ship.x - 10, self.ship.x + 10)
                hot = abs(self.ship.vy) > 1.0 or abs(self.ship.vx) > 0.30 or not level

                self.label.text = f'vx:{self.ship.vx:+4.2f} vy:{self.ship.vy:+4.2f} r:{self.ship.r:4.2f} l:{level}'
                self.label.color = 'red' if hot else 'white'

                if not self.mtdata.is_above_ground(self.ship, adj) and self.ship.vy < 0:
                    if hot:
                        self.crash()
                    else:
                        self.land()
                    self.ship.y = self.mtdata.get_y(self.ship.x) + adj

        self.update_scale()

        self.ship.position = (self.size.x / self.scale / 2, self.ship.y)
        self.mt.position = ((self.size.x / self.scale / 2) - self.ship.x, 0)

        self.update_status()

    def update_status(self):
        self.stats.text = 'f: {:+4.0f}  a: {:4.2f}  r: {:+5.3f} {:+5.3f}  p: {:+4.1f},{:+4.0f},{:+4.0f} l: {:}'.format(
            self.ship.fuel, self.ship.a * 10, self.ship.ar * 1000, self.ship.vr * 1000, self.ship.rotation, self.ship.x, self.ship.y, self.landings)

    def touch_began(self, touch):
        if self.running:
            self.touch_home = touch.location
        else:
            self.reset()

    def touch_moved(self, touch):
        if self.running:
            self.thrust_ramp = 0
            self.ship.set_thrust(max((-touch.location.y + self.touch_home.y - 5) / 10, 0))
            if not self.landed and abs(touch.location.x - self.touch_home.x) > 20:
                self.ship.rotate((touch.location.x - self.touch_home.x) / 50)
            else:
                self.ship.rotate(0.0)

    def touch_ended(self, touch):
        self.ship.thrust_ramp = 0.5
        self.ship.rotate(0)

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

    def update_scale(self):
        if self.ship.y > self.size.h * 0.75:
            value = self.size.h * 0.75 / abs(self.ship.y) + 0.01
        else:
            value = 1.0

        value = abs(value)
        self.scale = value

        self.stats.position = (self.size.w / self.scale / 2, (self.size.h - 40) / value)
        self.stats.scale = 1 / value
        self.label.position = (self.size.w / self.scale / 2, (self.size.h - 20) / value)
        self.label.scale = 1 / value

    def fire(self):
        path = make_path([(0, 0), (0, 1)])
        path.line_width = 2
        path.line_cap_style = ui.LINE_CAP_ROUND
        path.line_join_style = ui.LINE_JOIN_ROUND
        bullet = ShapeNode(path=path, fill_color='clear', stroke_color='white', parent=self)

        r = self.ship.rotation
        cannon = Point(math.cos(r), math.sin(r)) * 20
        bullet.position = self.ship.position + cannon
        end = bullet.position + Point(math.cos(r), math.sin(r)) * 350

        bullet.run_action(A.sequence(A.move_to(end.x, end.y, 1.5), A.remove()))
        
        sound.play_effect('fire.mp3', looping=False, volume=0.0)

    def drop_ship(self, length):
        x = random.uniform(length / 8, length * 7 / 8)

        while x < length:
            if self.mtdata.is_level(x - 10, x + 10):
                break
            x += 30

        self.ship.x = x
        self.ship.y = self.mtdata.get_y(x)
        self.landed = True

        print('dropped:', self.ship.x, self.ship.y, self.ship.r)

    def crash(self):
        print('crash', self.ship.vx, self.ship.vy)

        self.ship.crash()
        self.ship.remove_from_parent()

        self.running = False

    def land(self):
        self.landed = True
        # only give credit for a real flight
        if self.ship.maxalt - self.ship.y > 15:
            self.ship.maxalt = self.ship.y
            self.landings += 1

    def reset(self):
        self.ship.null()
        self.drop_ship(5000)
        self.add_child(self.ship)
        self.label.text = ''
        self.running = True
        self.paused = False
    

if __name__ == '__main__':
    sound.stop_all_effects()
    run(MyScene(), show_fps=False)

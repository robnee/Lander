from scene import *
import ui
import sound
import random
import math
A = Action


class Particle:
    '''Physics for partical motion in 2D space'''
    def __init__(self):
        self.m = 0
        self.r = 0
        self.ar = 0.0
        self.vr = 0.0
        self.ax = 0.0
        self.ay = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.x = 0
        self.y = 0
        
    def update(self):
        self.vr = self.vr * 0.98 + self.ar
        self.r += self.vr
        
        gx, gy, gz = gravity()
        gx, gy = 0, -0.025
        self.vx = self.vx * 0.999 + self.ax + gx
        self.vy = self.vy * 0.999 + self.ay + gy
        self.x += self.vx
        self.y += self.vy
        
    def get_a(self):
        return abs(Point(self.ax, self.ay))


class Part(ShapeNode, Particle):
    def __init__(self, pt):
        path = ui.Path()
        path.line_width = 1.5
        path.line_cap_style = ui.LINE_CAP_ROUND
        path.line_join_style = ui.LINE_JOIN_ROUND
        path.move_to(0, 0)
        path.line_to(pt.x, pt.y)
        ShapeNode.__init__(self, path=path, fill_color='clear', stroke_color='#bbb')
        Particle.__init__(self)
        
        
class Ship(ShapeNode, Particle):
    '''Player's ship'''
    def __init__(self):
        ShapeNode.__init__(self, path=self.ship_path(), fill_color='clear', stroke_color='#bbb')
        Particle.__init__(self)
        
        self.no_flame = ui.Path()
        self.flame = ShapeNode(path=self.no_flame, fill_color=(0, 0.0, 1.0, 0.4), stroke_color=(0, 1.0, 1.0, 0.5), parent=self)
        self.ljet = ShapeNode(path=self.no_flame, fill_color=(0, 0, 1.0, 0.1), stroke_color=(0, 1.0, 1.0, 0.5), parent=self)
        self.rjet = ShapeNode(path=self.no_flame, fill_color=(0, 0, 1.0, 0.1), stroke_color=(0, 1.0, 1.0, 0.5), parent=self)
        
        self.fuel = 5000
        self.mass = 1000
        self.thrust = 0
            
    def null(self):
        self.r = math.pi/2
        self.vr = 0
        self.vx = 0
        self.vy = 0
  
    def update(self, dt):
        dfuel = self.thrust * 10 * dt
        if self.fuel < dfuel:
            self.set_thrust(self.fuel / (10 * dt))
            self.fuel = 0
        else:  
            self.fuel -= dfuel
        
        force = self.thrust * 50 # units
        
        a = force / (self.mass + self.fuel)
        self.ax = math.cos(self.r) * a
        self.ay = math.sin(self.r) * a
        
        Particle.update(self)
        
    def set_thrust(self, level):
        if self.fuel <= 0:
            level = 0
            
        self.thrust = level
            
        self.flame.path = self.flame_path(level)
        self.flame.position = ((-30 - self.flame.path.bounds.w) / 2, 0)
        
    def rotate(self, level):
        #force =
        self.ar = max(min(-level / 1000, 0.01), -0.01)

        tail = self.ar * 10000
        
        path = ui.Path()
        path.line_width = 2
        path.line_cap_style = ui.LINE_CAP_ROUND
        path.line_join_style = ui.LINE_JOIN_ROUND
        path.move_to(0, 0)
        path.line_to(0, tail)
                        
        if tail > 1:
            self.ljet.position = (10, -5 - tail / 2)
            self.ljet.path = path
            self.rjet.path = self.no_flame
        elif tail < -1:
            self.rjet.position = (10, 5 - tail/2)
            self.rjet.path = path
            self.ljet.path = self.no_flame
        else:
            self.rjet.path = self.no_flame
            self.ljet.path = self.no_flame

    def ship_path(self):
        path = ui.Path()
        path.line_width = 1.5
        path.line_cap_style = ui.LINE_CAP_ROUND
        path.line_join_style = ui.LINE_JOIN_ROUND
        path.move_to(0, 0)
        path.line_to(30, 10)
        path.line_to(0, 20)
        path.line_to(5, 10)
        path.line_to(0, 0)
        
        return path
        
    def flame_path(self, level):
        path = ui.Path()
        if level > 0:
            tail = level * 40
        
            path.line_width = 1.25
            path.line_cap_style = ui.LINE_CAP_ROUND
            path.line_join_style = ui.LINE_JOIN_ROUND
            path.move_to(0, 0)
            path.line_to(-tail, 5)
            path.line_to(0, 10)
            path.line_to(-3, 5)
            path.line_to(0, 0)

        return path
        
        
class Mountain:
    def __init__(self, size):
        self.points = list()
        self.points.append(Point(10, 10))
        x, y = 10, 10
        while x < size.w:
            dx = random.uniform(50, 100)
            if random.uniform(0, 1) < 0.5:
                dy = random.uniform(-size.h, size.h)
            else:
                dy = 0
            x = min(x + dx, size.w)
            y = max(y + dy, 10)
            p = Point(x, y)
            self.points.append(p)
        
    def gen_path(self, scale):
        path = ui.Path()
        path.move_to(0, 0)
        for p in self.points:
            path.line_to(p.x/scale, -p.y/scale)

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
        
        
class MyScene(Scene):
    def setup(self):
        self.label = LabelNode(text='', font=('Helvetica Neue', 20), parent=self)
        self.label.position = (self.size.w / 2, self.size.h - 20)
        
        self.stats = LabelNode(text='stats', font=('Menlo', 16), parent=self)
        self.stats.position = (self.size.w / 2, self.size.h - 40)
        self.stats.z_position = 5
        
        self.mtdata = Mountain(Size(5000, 300))
        path = self.mtdata.gen_path(3)
        path.line_width = 1.0
        path.line_cap_style = ui.LINE_CAP_ROUND
        path.line_join_style = ui.LINE_JOIN_ROUND

        self.mt = ShapeNode(path=path, fill_color=self.background_color, stroke_color='#bbb', parent=self)
        self.mt.scale = 3
        self.mt.anchor_point = (0, 0)
        self.z_position = 0
        
        self.ship = Ship()
        self.ship.z_position = 1
        self.add_child(self.ship)
        
        self.landings = 0
        self.set_scale()
        self.reset()
    
    def did_change_size(self):
        pass
    
    def update(self):
        for c in self.children:
            if isinstance(c, Part):
                c.update()
                c.rotation = c.r
                c.position = ((self.size.x / self.scale / 2) + c.x - self.ship.x, c.y)

        if self.running:
            self.ship.update(self.dt)

            y = self.mtdata.get_y(self.ship.x) + 20

            if self.landed:
                if self.ship.y > y:
                    self.landed = False
                    self.label.text = ''
                else:
                    self.ship.y = y
                    self.ship.null()
            elif self.ship.y < y and self.ship.vy < 0:
                level = self.mtdata.is_level(self.ship.x - 10, self.ship.x + 10)
                self.label.text = 'vx:{:4.2f} vy:{:4.2f} l:{:}'.format(self.ship.vx, self.ship.vy, level)
                if self.ship.vy < -1 or abs(self.ship.vx) > 0.30 or not level:
                    self.crash()
                else:
                    self.land()
                self.ship.y = y

        self.set_scale()

        self.ship.rotation = self.ship.r
        self.ship.position = (self.size.x / self.scale / 2, self.ship.y)
        self.mt.position = ((self.size.x / self.scale / 2) - self.ship.x, 0)

        self.update_status()

    def update_status(self):
        self.stats.text = 'f: {:+4.0f}  a: {:4.2f}  r: {:+5.3f} {:+5.3f}  v: {:+5.2f},{:+5.2f}  p: {:+4.1f},{:+4.0f},{:+4.0f} l: {:}'.format(
            self.ship.fuel, self.ship.get_a() * 10, self.ship.ar * 1000, self.ship.vr * 1000, self.ship.vx,
            self.ship.vy, self.ship.rotation, self.ship.x, self.ship.y, self.landings)

    def touch_began(self, touch):
        if self.running:
            self.touch_home = touch.location
        else:
            self.reset()

    def touch_moved(self, touch):
        if self.running:
            self.ship.set_thrust(max((touch.location.y - self.touch_home.y - 5) / 10, 0))
            if abs(touch.location.x - self.touch_home.x) > 10:
                self.ship.rotate(-(touch.location.x - self.touch_home.x) / 40)

    def touch_ended(self, touch):
        self.ship.set_thrust(0)
        self.ship.rotate(0)

    def controller_changed(self, id, key, value):
        if key == 'thumbstick_left':
            self.ship.rotate(value[0])
        elif key == 'trigger_right':
            self.ship.set_thrust(value)
        elif key == 'button_b' and value:
            self.fire()
        elif key == 'button_x' and value:
            self.reset()
        elif key == 'button_y' and value:
            self.ship.fuel += 100

    def set_scale(self):
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
        path = ui.Path()
        path.line_width = 2
        path.line_cap_style = ui.LINE_CAP_ROUND
        path.line_join_style = ui.LINE_JOIN_ROUND
        path.move_to(0, 0)
        path.line_to(0, 1)
        bullet = ShapeNode(path=path, fill_color='clear', stroke_color='white', parent=self)

        r = self.ship.rotation
        cannon = Point(math.cos(r), math.sin(r)) * 20
        bullet.position = self.ship.position + cannon
        end = bullet.position + Point(math.cos(r), math.sin(r)) * 350

        bullet.run_action(A.sequence(A.move_to(end.x, end.y, 1.5)))

    def drop_ship(self, length):
        x = random.uniform(length/8, length * 7 / 8)

        while x < length:
            if self.mtdata.is_level(x - 10, x + 10):
                break
            x += 10

        self.ship.x = x
        self.ship.y = self.mtdata.get_y(x)
        self.landed = True

        print('dropped:', self.ship.x, self.ship.y)

    def crash(self):
        print('crash', self.ship.vx, self.ship.vy)

        sound.play_effect('explosion_large_distant.mp3')
        self.ship.fuel = max(self.ship.fuel - 50, 0)
        self.ship.remove_from_parent()

        for x in [10, 10, 30, 30]:
            p = Part(Point(x, 0))
            p.x, p.y = self.ship.x, self.ship.y

            p.vr = random.uniform(0.1, 0.3 )
            p.vx = self.ship.vx + random.uniform(-1, 1)
            p.vy = random.uniform(0, 3)
            p.run_action(A.sequence(A.fade_to(0.50, 2), A.remove()))
            self.add_child(p)

        self.running = False

    def land(self):
        self.landed = True
        self.landings += 1

    def reset(self):
        self.ship.null()
        self.drop_ship(5000)
        self.add_child(self.ship)
        self.label.text = ''
        self.running = True
    

if __name__ == '__main__':
    run(MyScene(), show_fps=False)

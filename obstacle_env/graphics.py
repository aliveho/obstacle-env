from __future__ import print_function
from __future__ import division

import datetime
import shutil

import numpy as np
import pygame
import os


class EnvViewer(object):
    """
        A viewer to render a highway driving environment.
    """
    SCREEN_WIDTH = 400
    SCREEN_HEIGHT = 400

    # TODO: move video recording to a monitoring wrapper
    VIDEO_SPEED = 2
    OUT_FOLDER = 'out'
    TMP_FOLDER = os.path.join(OUT_FOLDER, 'tmp')

    def __init__(self, env, record_video=True):
        self.env = env
        self.record_video = record_video

        pygame.init()
        pygame.display.set_caption("Obstacle-env")
        panel_size = (self.SCREEN_WIDTH, self.SCREEN_HEIGHT)
        self.screen = pygame.display.set_mode([self.SCREEN_WIDTH, self.SCREEN_HEIGHT])
        self.sim_surface = SimulationSurface(panel_size, 0, pygame.Surface(panel_size))
        self.clock = pygame.time.Clock()

        if self.record_video:
            self.frame = 0
            self.make_video_dir()
            self.video_name = 'obstacle_{}'.format(datetime.datetime.now().strftime('%Y-%m-%d-%H:%M:%S'))

    def handle_events(self):
        """
            Handle pygame events by forwarding them to the display and environment vehicle.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.env.close()
            self.sim_surface.handle_event(event)
            # if self.env.dynamics:
                # DynamicsGraphics.handle_event(self.env.vehicle, event)

    def display(self):
        """
            Display the scene on a pygame window.
        """
        self.sim_surface.move_display_window_to(self.window_position())
        Scene2dGraphics.display(self.env.scene, self.sim_surface)
        Scene2dGraphics.display_dynamics(self.env.dynamics, self.sim_surface)
        self.screen.blit(self.sim_surface, (0, 0))
        self.clock.tick(self.env.SIMULATION_FREQUENCY)
        pygame.display.flip()

        if self.record_video:
            self.frame += 1
            pygame.image.save(self.screen, "{}/{}_{:04d}.bmp".format(self.TMP_FOLDER,
                                                                     self.video_name,
                                                                     self.frame))

    def window_position(self):
        """
        :return: the world position of the center of the displayed window.
        """
        if self.env.dynamics:
            return self.env.dynamics.position
        else:
            return np.array([0, 0])

    def make_video_dir(self):
        """
            Make a temporary directory to hold the rendered images. If already existing, clear it.
        """
        if not os.path.exists(self.OUT_FOLDER):
            os.mkdir(self.OUT_FOLDER)
        self.clear_video_dir()
        os.mkdir(self.TMP_FOLDER)

    def clear_video_dir(self):
        """
            Clear the temporary directory containing the rendered images.
        """
        if os.path.exists(self.TMP_FOLDER):
            shutil.rmtree(self.TMP_FOLDER, ignore_errors=True)

    def close(self):
        """
            Close the pygame window.

            If video frames were recorded, convert them to a video/gif file
        """
        pygame.quit()
        if self.record_video:
            os.system("ffmpeg -r {3} -i {0}/{2}_%04d.bmp -vcodec libx264 -crf 25 {1}/{2}.avi"
                      .format(self.TMP_FOLDER,
                              self.OUT_FOLDER,
                              self.video_name,
                              self.VIDEO_SPEED * self.env.SIMULATION_FREQUENCY))
            delay = int(np.round(100 / (self.VIDEO_SPEED * self.env.SIMULATION_FREQUENCY)))
            os.system("convert -delay {3} -loop 0 {0}/{2}*.bmp {1}/{2}.gif"
                      .format(self.TMP_FOLDER,
                              self.OUT_FOLDER,
                              self.video_name,
                              delay))
            self.clear_video_dir()


class SimulationSurface(pygame.Surface):
    """
           A pygame Surface implementing a local coordinate system so that we can move and zoom in the displayed area.
    """
    BLACK = (0, 0, 0)
    GREY = (100, 100, 100)
    GREEN = (50, 200, 0)
    YELLOW = (200, 200, 0)
    WHITE = (255, 255, 255)
    SCALING_FACTOR = 1.3
    MOVING_FACTOR = 0.1

    def __init__(self, size, flags, surf):
        """
            New window surface.
        """
        super(SimulationSurface, self).__init__(size, flags, surf)
        self.origin = np.array([0, 0])
        self.scaling = 15.0
        self.centering_position = 0.5

    def pix(self, length):
        """
            Convert a distance [m] to pixels [px].

        :param length: the input distance [m]
        :return: the corresponding size [px]
        """
        return int(length * self.scaling)

    def pos2pix(self, x, y):
        """
            Convert two world coordinates [m] into a position in the surface [px]

        :param x: x world coordinate [m]
        :param y: y world coordinate [m]
        :return: the coordinates of the corresponding pixel [px]
        """
        return self.pix(x - self.origin[0, 0]), self.pix(y - self.origin[1, 0])

    def vec2pix(self, vec):
        """
             Convert a world position [m] into a position in the surface [px].
        :param vec: a world position [m]
        :return: the coordinates of the corresponding pixel [px]
        """
        return self.pix(vec[0]), self.pix(vec[1])

    def rect(self, rect):
        x, y = self.pos2pix(rect[0], rect[1])
        dx, dy = self.vec2pix(rect[2:4])
        return [x, y, dx, dy]

    def move_display_window_to(self, position):
        """
            Set the origin of the displayed area to center on a given world position.
        :param position: a world position [m]
        """
        self.origin = position - np.array(
            [[self.centering_position * self.get_width() / self.scaling], [self.get_height() / (2 * self.scaling)]])

    def handle_event(self, event):
        """
            Handle pygame events for moving and zooming in the displayed area.

        :param event: a pygame event
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_l:
                self.scaling *= 1 / self.SCALING_FACTOR
            if event.key == pygame.K_o:
                self.scaling *= self.SCALING_FACTOR
            if event.key == pygame.K_m:
                self.centering_position -= self.MOVING_FACTOR
            if event.key == pygame.K_k:
                self.centering_position += self.MOVING_FACTOR


class Scene2dGraphics(object):
    WHITE = (255, 255, 255)
    GREY = (100, 100, 100)

    @staticmethod
    def display(scene, surface):
        pygame.draw.rect(surface, Scene2dGraphics.WHITE, [0, 0, surface.get_width(), surface.get_height()], 0)
        for obstacle in scene.obstacles:
            position = surface.pos2pix(obstacle['position'][0, 0], obstacle['position'][1, 0])
            pygame.draw.circle(surface, Scene2dGraphics.GREY, position, surface.pix(obstacle['radius']), 0)

    @staticmethod
    def display_dynamics(dynamics, surface):
        position = surface.pos2pix(dynamics.position[0, 0], dynamics.position[1, 0])
        pygame.draw.circle(surface, Scene2dGraphics.GREY, position, surface.pix(0.2), 1)

    # def display(self, ax):
    #     psi = np.repeat(np.arange(0, 2 * math.pi, 2 * math.pi / np.size(self.grid)), 2)
    #     psi = np.hstack((psi[1:], [psi[0], psi[0]]))
    #     r = np.repeat(np.minimum(self.grid, CircularGrid.DISPLAY_DISTANCE_MAX), 2)
    #     r = np.hstack((r, [r[0]]))
    #     ax.plot(self.origin[0]+r*np.cos(psi), self.origin[1]+r*np.sin(psi), 'k')
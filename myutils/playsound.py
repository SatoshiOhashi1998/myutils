import pygame
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
decide_path = os.path.join(base_dir, "mp3/decide.mp3")
success_path = os.path.join(base_dir, "mp3/success.mp3")
alert_path = os.path.join(base_dir, "mp3/alert.mp3")
error_path = os.path.join(base_dir, "mp3/error.mp3")


def sound(sound_path):
    pygame.init()
    pygame.mixer.init()
    pygame.mixer.music.load(sound_path)
    pygame.mixer.music.play()

    # 再生終了まで待つ
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)


def decide():
    sound(decide_path)


def success():
    sound(success_path)


def alert():
    sound(alert_path)


def error():
    sound(error_path)

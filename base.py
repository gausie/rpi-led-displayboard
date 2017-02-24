import time
import sys
import os
import yaml


class FakeModule(object):
    def __getattr__(self, name):
        print(self, name)


env = os.getenv('ENV', 'development')

if (env == 'development'):
    sys.modules['rgbmatrix'] = FakeModule()

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/..'))
from rgbmatrix import RGBMatrix, RGBMatrixOptions  # noqa


class Base(object):
    def run(self):
        print('Running')

    def draw(self, image):
        if (env == 'development'):
            resized = image.copy().resize([500, 250])
            resized.show(title='RGB', command='display -sample \'500%\'')
        else:
            self.matrix.SetImage(image.convert('RGB'))

    def optionsFromConfig(self, config):
        options = RGBMatrixOptions()

        options.rows = config.get('rows')
        options.chain_length = config.get('chain')
        options.parallel = config.get('parallel')
        options.pwm_bits = config.get('pwm_bits')
        options.brightness = config.get('brightness')
        options.pwm_lsb_nanoseconds = config.get('pwm_lsb_nanoseconds')
        options.hardware_mapping = config.get('gpio_mapping')
        options.gpio_slowdown = config.get('slowdown_gpio')
        options.disable_hardware_pulsing = config.get('no_hardware_pulse')

        if config.get('show_refresh'):
            options.show_refresh_rate = 1

        return options

    def process(self):
        with open('config.yaml', 'r') as ymlfile:
            self.config = yaml.load(ymlfile)

        if (env == 'production'):
            led_config = self.config['led']
            options = self.optionsFromConfig(led_config)
            self.matrix = RGBMatrix(options=options)

        try:
            # Start loop
            print('Press CTRL-C to stop sample')
            self.run()
        except KeyboardInterrupt:
            print('Exiting\n')
            sys.exit(0)

        return True

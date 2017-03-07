#!/usr/bin/env python
from base import Base
from PIL import Image, ImageDraw, ImageFont
import glob
import re
import time
import os
import urllib.request as request
import json
import hashlib
from itertools import cycle


class Displayboard(Base):
    def __init__(self, *args, **kwargs):
        super(Base, self).__init__(*args, **kwargs)

    def drawBlank(self):
        draw = ImageDraw.Draw(self.image)

        draw.rectangle([(0, 0), (self.width, self.height)], '#000', '#000')

        del draw

    def get_latest_file(self, prefix):
        files = glob.glob('/tmp/{}-[0-9]*.json'.format(prefix))

        if len(files) == 0:
            return False

        return files[0]

    def retrieve_data(self, name, download_method, decay=600):
        filename = self.get_latest_file(name)

        if filename is False:
            data = download_method()
        else:
            search = re.search('/tmp/{}-([0-9]+).json'.format(name), filename)
            lastTime = search.group(1) if search is not None else 0

            if (time.time() - int(lastTime)) > decay:
                os.remove(filename)
                data = download_method()
            else:
                with open(filename, 'r') as file:
                    data = file.read()

        return json.loads(data)

    def downloadForecasts(self):
        weather_config = self.config.get('weather')
        key = weather_config.get('darksky_key')
        lat = weather_config.get('latitude')
        lng = weather_config.get('longitude')

        template = 'https://api.darksky.net/forecast/{}/{!s},{!s}?units=si'
        url = template.format(key, lat, lng)

        data = request.urlopen(url).read().decode('utf-8')

        now = int(time.time())
        filename = '/tmp/forecast-{!s}.json'.format(now)
        with open(filename, 'w') as file:
            file.write(data)

        return data

    def getHourlyForecasts(self, hours=False):
        forecasts = self.retrieve_data('forecast', self.downloadForecasts)

        if(hours is False):
            hours = round(self.width / 2) + 1

        return forecasts['hourly']['data'][:hours]

    def drawTemp(self, fraction):
        # Get temperatures from forecasts
        temps = [float(temp['temperature']) for temp in self.forecasts]

        temps_to_show = temps
        animation_period = 0.075
        if fraction < animation_period:
            n_to_show = max(1, (fraction / animation_period) * len(temps))
            temps_to_show = temps[:int(n_to_show)]

        # Create coordinates of line to be drawn at the bottom of the image
        low = min(temps)

        coordinates = [
            (i*2, self.height - 1 - round(temp - low))
            for i, temp in enumerate(temps_to_show)
        ]

        # Start a drawing action
        draw = ImageDraw.Draw(self.image)

        # Draw the temperature graph
        draw.line(coordinates, '#FF0000')

        # Label the first temperature
        draw.text(
            (0, coordinates[0][1] - self.fontHeight - 1),
            str(round(temps[0])),
            font=self.font
        )

        # Finally, destroy the reference to the drawing action
        del draw

    def drawWeather(self):
        # Get weather icons from forecasts
        weathers = list(enumerate([f['icon'] for f in self.forecasts]))

        last_icon = None
        for (index, icon) in weathers:
            if icon != last_icon:
                icon_image = Image.open('./icons/' + icon + '.ppm')
                self.image.paste(icon_image, (index * 2, 0))
                last_icon = icon

    def drawSceneWeather(self, fraction):
        self.forecasts = self.getHourlyForecasts()
        self.drawTemp(fraction)
        self.drawWeather()

    def downloadBusTimes(self):
        bus_config = self.config.get('edinburgh_bus')
        api_key = bus_config.get('api_key')
        stop_id = bus_config.get('stop_id')

        date_formatted = time.strftime('%Y%m%d%H')
        unhashed_key = api_key + date_formatted

        key = hashlib.md5(unhashed_key.encode('utf-8')).hexdigest()

        template = 'http://ws.mybustracker.co.uk/?key={}&module=json'
        base_url = template.format(key)

        url = '{}&function=getBusTimes&stopId={}'.format(base_url, stop_id)

        data = request.urlopen(url).read().decode('utf-8')

        now = int(time.time())
        filename = '/tmp/edinburgh_bus-{!s}.json'.format(now)
        with open(filename, 'w') as file:
            file.write(data)

        return data

    def drawBusTimes(self):
        tracked_buses = self.config.get('edinburgh_bus').get('services')
        tracked_bus_times = [
            bus for bus in self.bus_times['busTimes']
            if bus['mnemoService'] in tracked_buses
        ]

        draw = ImageDraw.Draw(self.image)

        for (index, bus) in enumerate(tracked_bus_times):
            bus_number = bus['mnemoService'].rjust(2)
            minutes = [str(time['minutes']) for time in bus['timeDatas']]
            line = '{!s}:{}'.format(bus_number, ','.join(minutes))

            draw.text((0, index * 6), line, font=self.font)

        del draw

    def drawAnimatedBus(self, fraction):
        bus_image = Image.open('./icons/edinburgh-bus.ppm')
        (width, height) = bus_image.size

        bump = (1 if int(fraction * 100) % 10 == 0 else 0)
        x = int(fraction * (32 + width)) - width
        y = self.height - height - bump

        self.image.paste(bus_image, (x, y))

    def drawSceneBus(self, fraction):
        self.bus_times = self.retrieve_data('edinburgh_bus',
                                            self.downloadBusTimes,
                                            30)

        self.drawBusTimes()
        self.drawAnimatedBus(fraction)

    def run(self):
        self.font = ImageFont.load(self.config['fontPath'])
        self.fontHeight = self.config['fontHeight']

        interval = int(self.config.get('sceneInterval', 10))
        frame_delay = int(self.config.get('frameDelay', 0))

        interval_start = time.time()

        scene_cycle = cycle([0, 1])
        scene = next(scene_cycle)

        while True:
            now = time.time()
            frame_time = now - interval_start
            fraction = frame_time / interval
            if fraction > 1:
                interval_start = now
                scene = next(scene_cycle)

            self.drawBlank()

            if scene == 0:
                self.drawSceneWeather(fraction)

            if scene == 1:
                self.drawSceneBus(fraction)

            self.draw()

            time.sleep(frame_delay)


# Main function
if __name__ == "__main__":
    displayboard = Displayboard()
    if (not displayboard.process()):
        displayboard.print_help()

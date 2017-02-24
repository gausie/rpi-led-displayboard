#!/usr/bin/env python
from base import Base
from PIL import Image, ImageDraw, ImageFont
from collections import Counter
import glob
import re
import time
import os
import urllib.request as request
import json


class Displayboard(Base):
    def __init__(self, *args, **kwargs):
        super(Base, self).__init__(*args, **kwargs)

    def getLatestForecastsFile(self):
        files = glob.glob('/tmp/forecast-[0-9]*.json')

        if len(files) == 0:
            return False

        return files[0]

    def getForecasts(self):
        filename = self.getLatestForecastsFile()

        if filename is False:
            forecasts = self.downloadForecasts()
        else:
            search = re.search('/tmp/forecast-([0-9]+).json', filename)
            lastTime = search.group(1) if search is not None else 0

            if (time.time() - int(lastTime)) > 60 * 10:
                os.remove(filename)
                forecasts = self.downloadForecasts()
            else:
                with open(filename, 'r') as file:
                    forecasts = file.read()

        return json.loads(forecasts)

    def downloadForecasts(self):
        key = self.config.get('darksky_key')
        lat = self.config.get('latitude')
        lng = self.config.get('longitude')

        template = 'https://api.darksky.net/forecast/{}/{!s},{!s}?units=si'
        url = template.format(key, lat, lng)

        data = request.urlopen(url).read().decode('utf-8')

        now = time.time()
        filename = '/tmp/forecast-{!s}.json'.format(now)
        with open(filename, 'w') as file:
            file.write(data)

        return data

    def getHourlyForecasts(self, hours=False):
        forecasts = self.getForecasts()

        if(hours is False):
            hours = round(self.width / 2)

        return forecasts['hourly']['data'][:hours]

    def drawTemp(self):
        # Get temperatures from forecasts
        temps = [float(temp['temperature']) for temp in self.forecasts]

        # Create coordinates of line to be drawn at the bottom of the image
        low = min(temps)

        coordinates = [
            (i*2, self.height - 1 - round(temp - low))
            for i, temp in enumerate(temps)
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

    def run(self):
        self.width = self.config['width']
        self.height = self.config['height']

        self.font = ImageFont.load(self.config['fontPath'])
        self.fontHeight = self.config['fontHeight']
        self.image = Image.new('RGB', [self.width, self.height])
        self.forecasts = self.getHourlyForecasts()

        self.drawTemp()
        self.drawWeather()
        self.draw(self.image)


# Main function
if __name__ == "__main__":
    displayboard = Displayboard()
    if (not displayboard.process()):
        displayboard.print_help()

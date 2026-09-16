from PIL import Image
import os
import random

width, height = 3000, 3000
img = Image.new('RGB', (width, height))
pixels = img.load()

for x in range(width):
    for y in range(height):
        pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

img.save('test_large.jpg', quality=95)
print(os.path.getsize('test_large.jpg'))

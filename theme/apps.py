from tailwind.apps import TailwindConfig


class ThemeConfig(TailwindConfig):
    name = 'theme'
    path = 'theme/static/css'  # The path where your Tailwind CSS will be generated
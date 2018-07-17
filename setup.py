from distutils.core import setup

setup(
    name="Home Automation Heating",
    version="1.0",
    description="Home Automation Hub Module - Heating",
    author="Cameron Gray",
    author_email="development@camerongray.me",
    url="https://github.com/camerongray1515",
    install_requires=[
        "python-dateutil==2.7.3"
    ],
    packages=["home_automation_heating"],
)
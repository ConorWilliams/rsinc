import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="rsinc-ConorWilliams",
    version="0.0.1",
    author="ConorWilliams",
    author_email="conorwilliams@outlook.com",
    description="A tiny, hackable, two-way cloud synchronisation client for rclone",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ConorWilliams/rsinc",
    packages=setuptools.find_packages(),
    scripts=['bin/rsinc'],
    classifiers=[
        "Programming Language :: Python :: 3 ",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Unix",
    ],
)

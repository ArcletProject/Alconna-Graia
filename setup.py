import setuptools

setuptools.setup(
    name="arclet-alconna-graia",
    url="https://github.com/ArcletProject/Alconna-Graia",
    version="0.6.1",
    author="ArcletProject",
    author_email="rf_tar_railt@qq.com",
    description="Support Alconna to GraiaProject",
    license='AGPL-3.0',
    packages=['arclet.alconna.graia'],
    install_requires=[
        'arclet-alconna<1.3.0, >=1.2.0.7',
        'graia-saya~=0.0.16',
        'graia-ariadne<1.0.0, >=0.7.14',
        'graia-amnesia>=0.5.0',
        'graia-broadcast>=0.18.0',
        'creart~=0.2.1',
        'creart-graia~=0.1.5',
        'nepattern>=0.1.2'
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'creart.creators': [
            'alconna_behavior = arclet.alconna.graia.create:AlconnaBehaviorCreator'
        ]
    },
    keywords=['alconna', 'graia', 'dispatcher', 'arclet'],
    python_requires='>=3.8',
    project_urls={
        'Documentation': 'https://arcletproject.github.io/docs/alconna/tutorial',
        'Bug Reports': 'https://github.com/ArcletProject/Alconna/issues',
        'Source': 'https://github.com/ArcletProject/Alconna',
    },
)

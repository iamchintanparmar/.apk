"""
spec_template.py
----------------
Generates a buildozer.spec file for a converted Kivy project.
Author: Chintan Parmar
"""

SPEC_TEMPLATE = """\
[app]
title = {title}
package.name = {package_name}
package.domain = org.tk2apk.converted
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.arch = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
"""


def generate_spec(title: str, package_name: str) -> str:
    safe_name = "".join(c for c in package_name.lower() if c.isalnum()) or "convertedapp"
    return SPEC_TEMPLATE.format(title=title, package_name=safe_name)

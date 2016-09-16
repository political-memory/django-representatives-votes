from django import dispatch

sync = dispatch.Signal(providing_args=['instance'])

from django.template.defaulttags import register


@register.filter
def get_items(dictionary):
    return dictionary.values()


@register.filter
def multiply(value, arg):
    return value*arg

from odoo.exceptions import ValidationError

_MAX_FLOAT_TIME = 23 + (59 / 60)


def _raise_range_error(env, field_label=None):
    if field_label:
        raise ValidationError(
            env._('%(field)s must be between 00:00 and 23:59.', field=field_label),
        )
    raise ValidationError(env._('Time must be between 00:00 and 23:59.'))


def _raise_precision_error(env, field_label=None):
    if field_label:
        raise ValidationError(
            env._('%(field)s must use minute precision (HH:MM).', field=field_label),
        )
    raise ValidationError(env._('Time must use minute precision (HH:MM).'))


def normalize_time_value(value):
    if value in (False, None):
        return value
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value
    # Normalize to minute precision only. Range is validated separately.
    return int(round(value * 60)) / 60.0


def validate_time_value(env, value, field_label=None):
    if value in (False, None):
        return
    if value < 0 or value > _MAX_FLOAT_TIME:
        _raise_range_error(env, field_label)
    if abs(value * 60 - round(value * 60)) > 1e-6:
        _raise_precision_error(env, field_label)


def fill_name_parts_from_name(
    vals,
    name_field='name',
    part_fields=('last_name', 'first_name', 'middle_name'),
):
    result = dict(vals)
    raw_name = (result.get(name_field) or '').strip()
    has_name_parts = any(result.get(field_name) for field_name in part_fields)
    if not raw_name or has_name_parts:
        return result

    parts = [part for part in raw_name.split() if part]
    if not parts:
        return result

    result['last_name'] = parts[0]
    if len(parts) > 1:
        result['first_name'] = parts[1]
    if len(parts) > 2:
        result['middle_name'] = ' '.join(parts[2:])
    return result

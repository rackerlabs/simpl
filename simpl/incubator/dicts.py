# Copyright (c) 2011-2015 Rackspace US, Inc.
# All Rights Reserved.
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Helpers for built-in `dict` class."""


def write_path(target, path, value, separator='/'):
    """Write a value deep into a dict building any intermediate keys.

    :param target: a dict to write data to
    :param path: a key or path to a key (path is delimited by `separator`)
    :param value: the value to write to the key
    :keyword separator: the separator used in the path (ex. Could be "." for a
        json/mongodb type of value)
    """
    parts = path.split(separator)
    current = target
    for part in parts[:-1]:
        if part not in current:
            current[part] = current = {}
        else:
            current = current[part]
    current[parts[-1]] = value


def read_path(source, path, separator='/'):
    """Read a value from a dict supporting a deep path as a key.

    :param source: a dict to read data from
    :param path: a key or path to a key (path is delimited by `separator`)
    :keyword separator: the separator used in the path (ex. Could be "." for a
        json/mongodb type of value)
    """
    parts = path.strip(separator).split(separator)
    current = source
    for part in parts[:-1]:
        if part not in current:
            return
        current = current[part]
        if not isinstance(current, dict):
            return
    return current.get(parts[-1])


def path_exists(source, path, separator='/'):
    """Check a dict for the existence of a value given a path to it.

    :param source: a dict to read data from
    :param path: a key or path to a key (path is delimited by `separator`)
    :keyword separator: the separator used in the path (ex. Could be "." for a
        json/mongodb type of value)
    """
    if path == separator and isinstance(source, dict):
        return True
    parts = path.strip(separator).split(separator)
    if not parts:
        return False
    current = source
    for part in parts:
        if not isinstance(current, dict):
            return False
        if part not in current:
            return False
        current = current[part]
    return True


def split_dict(data, filter_keys=None):  # flake8: noqa
    """Deep extract matching keys into separate dict.

    Extracted data is placed into another dict. The function returns two dicts;
    one without the filtered data and one with only the filtered data. The
    dicts are structured so that they can be recombined into one dict. To
    accomplish that, all values extracted from lists are replaced with a `None`
    and `None` values are placed in extracted lists to maintain the position
    of the extracted data.

    One example use case for this is for extracting out sensitive data from a
    dict for encryption or separate storage:

        SENSITIVE_KEYS = [
            'apikey',
            re.compile('password$'),
            re.compile('^password'),
        ]

        safe, sensitive = split_dict(data, filter_keys=SENSITIVE_KEYS)

        original = merge_dictionary(safe, sensitive)

    :param filter_keys: a list of keys considered sensitive
    :returns: a tuple of two dicts; (original-extracted, extracted)
    """
    def key_match(key, filter_keys):
        """Determine whether or not key is in filter_keys."""
        if key in filter_keys:
            return True
        if key is None:
            return False
        for reg_expr in [pattern for pattern in filter_keys
                         if hasattr(pattern, "search")
                         and callable(getattr(pattern, "search"))]:
            if reg_expr.search(key):
                return True
        return False

    def recursive_split(data, filter_keys=None):
        """Return split dict or list if it contains any matching fields."""
        if filter_keys is None:  # Safer than default value
            filter_keys = []
        clean = None
        matching = None
        has_matching_data = False
        has_clean_data = False
        if isinstance(data, list):
            clean = []
            matching = []
            for value in data:
                if isinstance(value, dict):
                    clean_value, matching_value = recursive_split(
                        value, filter_keys=filter_keys)
                    if matching_value is not None:
                        matching.append(matching_value)
                        has_matching_data = True
                    else:
                        matching.append({})  # placeholder
                    if clean_value is not None:
                        clean.append(clean_value)
                        has_clean_data = True
                    else:
                        clean.append({})  # placeholder
                elif isinstance(value, list):
                    clean_value, matching_value = recursive_split(
                        value, filter_keys=filter_keys)
                    if matching_value is not None:
                        matching.append(matching_value)
                        has_matching_data = True
                    else:
                        matching.append([])  # placeholder
                    if clean_value is not None:
                        clean.append(clean_value)
                        has_clean_data = True
                    else:
                        clean.append([])
                else:
                    clean.append(value)
                    matching.append(None)  # placeholder
                    has_clean_data = True
        elif isinstance(data, dict):
            clean = {}
            matching = {}
            for key, value in data.items():
                if key_match(key, filter_keys):
                    has_matching_data = True
                    matching[key] = value
                elif isinstance(value, dict):
                    clean_value, matching_value = recursive_split(
                        value, filter_keys=filter_keys)
                    if matching_value is not None:
                        has_matching_data = True
                        matching[key] = matching_value
                    if clean_value is not None:
                        has_clean_data = True
                        clean[key] = clean_value
                elif isinstance(value, list):
                    clean_value, matching_value = recursive_split(
                        value, filter_keys=filter_keys)
                    if matching_value is not None:
                        has_matching_data = True
                        matching[key] = matching_value
                    if clean_value is not None:
                        has_clean_data = True
                        clean[key] = clean_value
                else:
                    has_clean_data = True
                    clean[key] = value
        if has_matching_data:
            if has_clean_data:
                return clean, matching
            else:
                return None, matching
        else:
            if has_clean_data:
                return clean, None
            else:
                return data, None
    clean, matching = recursive_split(data, filter_keys=filter_keys)
    return clean, matching


def merge_dictionary(dst, src, extend_lists=False):
    """Recursively merge two dicts.

    Hashes at the root level are NOT overwritten. This can be used to merge two
    dicts using deep key evaluation (with support for merging lists as well).

    There is also logic to handle placeholders (`None`) in lists as documented
    in split_dicts.

    :keyword extend_lists: if true, just extends lists instead of merging them.

    Note: This updates dst.
    """
    stack = [(dst, src)]
    while stack:
        current_dst, current_src = stack.pop()
        for key in current_src:
            source = current_src[key]
            if key not in current_dst:
                current_dst[key] = source
            else:
                dest = current_dst[key]
                if isinstance(source, dict) and isinstance(dest, dict):
                    stack.append((dest, source))
                elif isinstance(source, list) and isinstance(dest, list):
                    merge_lists(dest, source, extend_lists=extend_lists)
                else:
                    current_dst[key] = source
    return dst


def merge_lists(dest, source, extend_lists=False):
    """Recursively merge two lists.

    :keyword extend_lists: if true, just extends lists instead of merging them.

    This applies merge_dictionary if any of the entries are dicts.
    Note: This updates dest and returns it.
    """
    if not source:
        return
    if not extend_lists:
        # Make them the same size
        left = dest
        right = source[:]
        if len(dest) > len(source):
            right.extend([None] * (len(dest) - len(source)))
        elif len(dest) < len(source):
            left.extend([None] * (len(source) - len(dest)))
        # Merge lists
        for index, value in enumerate(left):
            if value is None and right[index] is not None:
                dest[index] = right[index]
            elif isinstance(value, dict) and isinstance(right[index], dict):
                merge_dictionary(dest[index], source[index],
                                 extend_lists=extend_lists)
            elif isinstance(value, list):
                merge_lists(value, right[index])
            elif right[index] is not None:
                dest[index] = right[index]
    else:
        dest.extend([src for src in source if src not in dest])
    return dest

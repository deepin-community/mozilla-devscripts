# Copyright (c) 2009-2011, Benjamin Drung <bdrung@debian.org>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

# Reference: https://developer.mozilla.org/en/Toolkit_version_format

import functools
import sys


@functools.total_ordering
class Part(object):
    """Mozilla version part in the format <number-a><string-b><number-c><string-d>."""
    def __init__(self, number_a, string_b, number_c, string_d):
        self.number_a = number_a
        self.string_b = string_b
        self.number_c = number_c
        self.string_d = string_d

    def __repr__(self):
        return "%s(%r, %r, %r, %r)" % (self.__class__.__name__, self.number_a, self.string_b,
                                       self.number_c, self.string_d)

    def __iter__(self):
        return iter((self.number_a, self.string_b, self.number_c, self.string_d))


    def __eq__(self, other):
        return ((self.number_a, self.string_b, self.number_c, self.string_d)
                == (other.number_a, other.string_b, other.number_c, other.string_d))

    def __lt__(self, other):
        # A string-part that exists is always less-then a nonexisting string-part
        return ((self.number_a, Subpart(self.string_b), self.number_c, Subpart(self.string_d))
                < (other.number_a, Subpart(other.string_b),
                    other.number_c, Subpart(other.string_d)))

    @classmethod
    def from_string(cls, part):
        """Decodes a version part (like 5pre4) to
           <number-a><string-b><number-c><string-d>"""
        number_a = 0
        string_b = ""
        number_c = 0
        string_d = ""

        # Split <number-a>
        length = 0
        for i in range(len(part)):
            if part[i].isdigit() or part[i] == "-":
                length += 1
            else:
                break
        if length > 0:
            number_a = int(part[0:length])
        part = part[length:]

        # Split <string-b>
        length = 0
        for i in range(len(part)):
            if not (part[i].isdigit() or part[i] == "-"):
                length += 1
            else:
                break
        string_b = part[0:length]
        part = part[length:]

        # Split <number-c>
        length = 0
        for i in range(len(part)):
            if part[i].isdigit() or part[i] == "-":
                length += 1
            else:
                break
        if length > 0:
            number_c = int(part[0:length])
        string_d = part[length:]

        # if string-b is a plus sign, number-a is incremented to be compatible with
        # the Firefox 1.0.x version format: 1.0+ is the same as 1.1pre
        if string_b == "+":
            number_a += 1
            string_b = "pre"

        # if the version part is a single asterisk, it is interpreted as an
        # infinitely-large number: 1.5.0.* is the same as 1.5.0.(infinity)
        if string_b == "*":
            number_a = sys.maxsize
            string_b = ""

        return cls(number_a, string_b, number_c, string_d)

    def convert_to_debian(self):
        """Converts a Mozilla version part (like 5pre4) to a Debian version."""
        debian_version = ""
        if self.string_d != "":
            debian_version = "~" + self.string_d
        if self.number_c != 0 or self.string_d != "":
            debian_version = str(self.number_c) + debian_version
        if self.string_b != "":
            debian_version = "~" + self.string_b + debian_version
        debian_version = str(self.number_a) + debian_version
        return debian_version


@functools.total_ordering
class Subpart(object):
    """Represent a sub-part of a Mozilla version (either a number or a string)."""

    def __init__(self, subpart):
        self.subpart = subpart

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.subpart)

    def __eq__(self, other):
        return self.subpart == other.subpart

    def __lt__(self, other):
        # A string-part that exists is always less-then a nonexisting string-part
        if self.subpart == "":
            return False
        if other.subpart == "":
            return self.subpart != ""

        return self.subpart < other.subpart


def decode_version(version, verbose=False):
    """Decodes a version string like 1.1pre1a"""
    decoded_parts = [Part.from_string(part) for part in version.split(".")]
    if verbose:
        print("I: Split %s up into %s." % (version, decoded_parts))
    return decoded_parts


def compare_versions(version1, version2, verbose=False):
    a = decode_version(version1, verbose)
    b = decode_version(version2, verbose)

    if len(a) < len(b):
        a += (len(b) - len(a)) * [Part(0, "", 0, "")]
    if len(b) < len(a):
        b += (len(a) - len(b)) * [Part(0, "", 0, "")]

    if a == b:
        return 0
    if a < b:
        return -1
    return 1


def extract_upstream_version(debian_version):
    # remove last part separated by a dash (1.0-2 -> 1.0)
    parts = debian_version.split('-')
    if len(parts) > 1:
        del parts[-1]
    upstream_version = '-'.join(parts)

    # remove epoch
    parts = upstream_version.split(':')
    if len(parts) > 1:
        del parts[0]
    upstream_version = ':'.join(parts)

    return upstream_version


def convert_debian_to_moz_version(debian_version):
    upstream_version = extract_upstream_version(debian_version)

    # compatibility: strip +nobinonly and +build
    parts = upstream_version.split('+')
    if len(parts) > 1 and parts[-1] == "nobinonly":
        del parts[-1]
    if len(parts) > 1 and parts[-1].startswith("build"):
        del parts[-1]
    upstream_version = '+'.join(parts)

    moz_version = upstream_version.replace("~", "")
    return moz_version


def convert_moz_to_debian_version(moz_version, epoch=0, verbose=False):
    parts = decode_version(moz_version, verbose)
    # tranform parts
    parts = [p.convert_to_debian() for p in parts]
    debian_version = ".".join(parts)
    if epoch != 0:
        debian_version = str(epoch) + ":" + debian_version
    return debian_version


def moz_to_next_debian_version(moz_version, epoch=0, verbose=False):
    """Convert a given Mozilla version to the next Debian version.

    Compared to convert_moz_to_debian_version it does following:
    * append 0 to a trailing letter, or
    * append + to a trailing number, or
    * replace a trailing * with +.

    Examples:
    9.0a => 9.0~a0
    9.0a1 => 9.0~a1+
    9.0 => 9.0+
    9.0.* => 9.0.+
    """
    parts = decode_version(moz_version, verbose)
    # tranform last parts
    (number_a, string_b, number_c, string_d) = parts[-1]
    last_part = ""
    if string_d != "":
        last_part = "~" + string_d + "0"
    if number_c != 0 or string_d != "":
        if last_part:
            last_part = str(number_c) + last_part
        else:
            if number_c == sys.maxsize:
                last_part = "+"
            else:
                last_part = str(number_c) + "+"
    if string_b != "":
        if last_part:
            last_part = "~" + string_b + last_part
        else:
            last_part = "~" + string_b + "0"
    if last_part:
        last_part = str(number_a) + last_part
    else:
        if number_a == sys.maxsize:
            last_part = "+"
        else:
            last_part = str(number_a) + "+"

    parts = [p.convert_to_debian() for p in parts[:-1]] + [last_part]
    debian_version = ".".join(parts)
    if epoch != 0:
        debian_version = str(epoch) + ":" + debian_version
    return debian_version

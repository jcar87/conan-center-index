import os

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.cmake import CMake, CMakeDeps, cmake_layout, CMakeToolchain
from conan.tools.files import get, rmdir

class Libxml2Conan(ConanFile):
    name = "libxml2"
    package_type = "library"
    url = "https://github.com/conan-io/conan-center-index"
    description = "libxml2 is a software library for parsing XML documents"
    topics = "xml", "parser", "validation"
    homepage = "https://gitlab.gnome.org/GNOME/libxml2/-/wikis/"
    license = "MIT"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "catalog": [True, False],
        "debug": [True, False],
        "html": [True, False],
        "http": [True, False],
        "iconv": [True, False],
        "icu": [True, False],
        "iso8859x": [True, False],
        "legacy": [True, False],
        "lzma": [True, False],
        "modules": [True, False],
        "output": [True, False],
        "pattern": [True, False],
        "programs": [True, False],
        "push": [True, False],
        "python": [True, False],
        "readline": [True, False],
        "regexps": [True, False],
        "sax1": [True, False],
        "tests": [True, False],
        "threads": [True, False],
        "tls": [True, False],
        "valid": [True, False],
        "xinclude": [True, False],
        "xpath": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "catalog": True,
        "debug": True,
        "html": True,
        "http": False,
        "iconv": True,
        "icu": False,
        "iso8859x": True,
        "legacy": False,
        "lzma": False,
        "modules": True,
        "output": True,
        "pattern": True,
        "programs": True,
        "push": True,
        "python": False,
        "readline": False,
        "regexps": True,
        "sax1": True,
        "tests": True,
        "threads": True,
        "tls": False,
        "valid": True,
        "xinclude": True,
        "xpath": True,
    }

    implements = ["auto_shared_fpic"]

    def configure(self):
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        if self.options.iconv:
            self.requires("libiconv/1.17")
        if self.options.lzma:
            self.requires("xz_utils/5.4.5")
        if self.options.icu:
            self.requires("icu/73.2")
        if self.options.python:
            pass # Python is not implemented for this recipe yet

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["LIBXML2_WITH_CATALOG"] = self.options.catalog
        tc.cache_variables["LIBXML2_WITH_DEBUG"] = self.options.debug
        tc.cache_variables["LIBXML2_WITH_HTML"] = self.options.html
        tc.cache_variables["LIBXML2_WITH_HTTP"] = self.options.http
        tc.cache_variables["LIBXML2_WITH_ICONV"] = self.options.iconv
        tc.cache_variables["LIBXML2_WITH_ICU"] = self.options.icu
        tc.cache_variables["LIBXML2_WITH_ISO8859X"] = self.options.iso8859x
        tc.cache_variables["LIBXML2_WITH_LEGACY"] = self.options.legacy
        tc.cache_variables["LIBXML2_WITH_LZMA"] = self.options.lzma
        tc.cache_variables["LIBXML2_WITH_MODULES"] = self.options.modules
        tc.cache_variables["LIBXML2_WITH_OUTPUT"] = self.options.output
        tc.cache_variables["LIBXML2_WITH_PATTERN"] = self.options.pattern
        tc.cache_variables["LIBXML2_WITH_PROGRAMS"] = self.options.programs
        tc.cache_variables["LIBXML2_WITH_PUSH"] = self.options.push
        tc.cache_variables["LIBXML2_WITH_PYTHON"] = self.options.python
        tc.cache_variables["LIBXML2_WITH_READLINE"] = self.options.readline
        tc.cache_variables["LIBXML2_WITH_REGEXPS"] = self.options.regexps
        tc.cache_variables["LIBXML2_WITH_SAX1"] = self.options.sax1
        tc.cache_variables["LIBXML2_WITH_TESTS"] = self.options.tests
        tc.cache_variables["LIBXML2_WITH_THREADS"] = self.options.threads
        tc.cache_variables["LIBXML2_WITH_TLS"] = self.options.tls
        tc.cache_variables["LIBXML2_WITH_VALID"] = self.options.valid
        tc.cache_variables["LIBXML2_WITH_XINCLUDE"] = self.options.xinclude
        tc.cache_variables["LIBXML2_WITH_XPATH"] = self.options.xpath
        tc.cache_variables["PKG_CONFIG_EXECUTABLE"] = "PKG_CONFIG_EXECUTABLE-NOTFOUND" 
        tc.generate()

        cmake_deps = CMakeDeps(self)
        cmake_deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["xml2"]
        if self.settings.os == "Windows" and not self.options.shared:
            self.cpp_info.libs = ["xml2s"]
        self.cpp_info.includedirs = [os.path.join("include", "libxml2")]
        if not self.options.shared:
            self.cpp_info.defines.append("LIBXML_STATIC")

        self.cpp_info.names["cmake_file_name"] = "libxml2"
        self.cpp_info.set_property("cmake_target_name", "LibXml2::LibXml2")
        self.cpp_info.set_property("cmake_additional_variables_prefixes", ["LIBXML2_"])

        is_unix = self.settings.os in ["Linux", "FreeBSD", "Macos"] or is_apple_os(self)

        if is_unix:
            self.cpp_info.system_libs.append("m")
            if self.options.modules:
                self.cpp_info.system_libs.append("dl")

        if self.settings.os in ("Linux", "FreeBSD") and self.options.threads:
            self.cpp_info.system_libs.append("pthread")

        if self.options.icu:
            self.cpp_info.requires.extend(["icu::icu-uc", "icu::icu-data", "icu::icu-i18n"])
        if self.settings.os == "Windows":
            self.cpp_info.system_libs.append("Bcrypt")
            if self.options.http:
                self.cpp_info.system_libs.append("ws2_32")

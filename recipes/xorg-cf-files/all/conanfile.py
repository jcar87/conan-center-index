import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=1.57.0"


class XorgCfFilesConan(ConanFile):
    name = "xorg-cf-files"
    description = "Imake configuration files & templates"
    topics = ("xorg", "template", "configuration", "obsolete")
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/util/cf"
    url = "https://github.com/conan-io/conan-center-index"
    settings = "os", "arch", "compiler", "build_type"

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("xorg-macros/1.19.3")
        self.requires("xorg-proto/2021.4")

    def build_requirements(self):
        self.tool_requires("pkgconf/1.7.4")
        if self._settings_build.os == "Windows" and not self.conf.get("tools.microsoft.bash:path", check_type=str):
            self.win_bash = True
            self.tool_requires("msys2/cci.latest")
        if is_msvc(self):
            self.tool_requires("automake/1.16.5")

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def validate(self):
        if is_apple_os(self):
            raise ConanInvalidConfiguration("This recipe does not support Apple operating systems.")

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.arch
        # self.info.settings.os  # FIXME: can be removed once c3i is able to test multiple os'es from one common package

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
                  destination=self.source_folder, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        env = tc.environment()
        if is_msvc(self):
            compile_wrapper = unix_path(self, self.conf.get("user.automake:compile-wrapper"))
            env.define("CC", f"{compile_wrapper} cl -nologo")
            env.define("CXX", f"{compile_wrapper} cl -nologo")
            env.define("CPP", f"{compile_wrapper} cl -nologo -E")
        tc.generate(env)

        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libdirs = []

        x11_config_files = os.path.join(self.package_folder, "lib", "X11", "config")
        self.conf_info.define("user.xorg-cf-files:config-path", x11_config_files)

        # TODO: remove once recipe is only compatible with Conan >= 2.0
        self.user_info.CONFIG_PATH = x11_config_files.replace("\\", "/")

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.gnu import AutotoolsToolchain, Autotools
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path


import glob
import os
import shutil


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    win_bash = True

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)
        if self._settings_build.os == "Windows" and not self.conf.get("tools.microsoft.bash:path", check_type=str):
            self.tool_requires("msys2/cci.latest")
    
    # def layout(self):
    #     basic_layout(self, src_folder="src")

    def generate(self):
        tc = AutotoolsToolchain(self)
        env = tc.environment()

        if is_msvc(self):
            self.output.warning(f"dependencies: {self.dependencies.build}")
            automake = self.dependencies.build["automake"] if getattr(self, "settings_build", None) else self.dependencies["automake"]
            compile_wrapper = unix_path(self, automake.conf_info.get("user.automake:compile-wrapper"))
            lib_wrapper = unix_path(self, automake.conf_info.get("user.automake:lib-wrapper"))
            self.output.warning(f"Compile wrapper: {compile_wrapper}")
            env.define("CC", f"{compile_wrapper} cl -nologo")
            env.define("CXX", f"{compile_wrapper} cl -nologo")
            env.define("AR", f"{lib_wrapper} lib")
            env.define("LD", "link")

        tc.generate(env)

        buildenv = VirtualBuildEnv(self)
        buildenv.generate()

    @property
    def _package_folder(self):
        return os.path.join(self.build_folder, "package")

    # def _build_autotools(self):
    #     """ Test autotools integration """
    #     # Copy autotools directory to build folder
    #     shutil.copytree(os.path.join(self.source_folder, "autotools"), os.path.join(self.build_folder, "autotools"))
    #     with tools.chdir("autotools"):
    #         self.run("{} --install --verbose -Wall".format(os.environ["AUTORECONF"]), win_bash=tools.os_info.is_windows)

    #     tools.mkdir(self._package_folder)
    #     conf_args = [
    #         "--prefix={}".format(tools.unix_path(self._package_folder)),
    #         "--enable-shared", "--enable-static",
    #     ]

    #     os.mkdir("bin_autotools")
    #     with tools.chdir("bin_autotools"):
    #         with self._build_context():
    #             autotools = AutoToolsBuildEnvironment(self, win_bash=tools.os_info.is_windows)
    #             autotools.libs = []
    #             autotools.configure(args=conf_args, configure_dir=os.path.join(self.build_folder, "autotools"))
    #             autotools.make(args=["V=1"])
    #             autotools.install()

    # def _test_autotools(self):
    #     assert os.path.isdir(os.path.join(self._package_folder, "bin"))
    #     assert os.path.isfile(os.path.join(self._package_folder, "include", "lib.h"))
    #     assert os.path.isdir(os.path.join(self._package_folder, "lib"))

    #     if not tools.cross_building(self):
    #         self.run(os.path.join(self._package_folder, "bin", "test_package"), run_environment=True)

    # def _build_ltdl(self):
    #     """ Build library using ltdl library """
    #     cmake = CMake(self)
    #     cmake.configure(source_folder="ltdl")
    #     cmake.build()

    # def _test_ltdl(self):
    #     """ Test library using ltdl library"""
    #     lib_suffix = {
    #         "Linux": "so",
    #         "FreeBSD": "so",
    #         "Macos": "dylib",
    #         "Windows": "dll",
    #     }[str(self.settings.os)]

    #     if not tools.cross_building(self):
    #         bin_path = os.path.join("bin", "test_package")
    #         libdir = "bin" if self.settings.os == "Windows" else "lib"
    #         lib_path = os.path.join(libdir, "liba.{}".format(lib_suffix))
    #         self.run("{} {}".format(bin_path, lib_path), run_environment=True)

    # def _build_static_lib_in_shared(self):
    #     """ Build shared library using libtool (while linking to a static library) """

    #     # Copy static-in-shared directory to build folder
    #     autotools_folder = os.path.join(self.build_folder, "sis")
    #     shutil.copytree(os.path.join(self.source_folder, "sis"), autotools_folder)

    #     install_prefix = os.path.join(autotools_folder, "prefix")

    #     # Build static library using CMake
    #     cmake = CMake(self)
    #     cmake.definitions["CMAKE_INSTALL_PREFIX"] = install_prefix
    #     cmake.configure(source_folder=autotools_folder, build_folder=os.path.join(autotools_folder, "cmake_build"))
    #     cmake.build()
    #     cmake.install()

    #     # Copy autotools directory to build folder
    #     with tools.chdir(autotools_folder):
    #         self.run("{} -ifv -Wall".format(os.environ["AUTORECONF"]), win_bash=tools.os_info.is_windows)

    #     with tools.chdir(autotools_folder):
    #         conf_args = [
    #             "--enable-shared",
    #             "--disable-static",
    #             "--prefix={}".format(tools.unix_path(os.path.join(install_prefix))),
    #         ]
    #         with self._build_context():
    #             autotools = AutoToolsBuildEnvironment(self, win_bash=tools.os_info.is_windows)
    #             autotools.libs = []
    #             autotools.link_flags.append("-L{}".format(tools.unix_path(os.path.join(install_prefix, "lib"))))
    #             autotools.configure(args=conf_args, configure_dir=autotools_folder)
    #             autotools.make(args=["V=1"])
    #             autotools.install()

    # def _test_static_lib_in_shared(self):
    #     """ Test existence of shared library """
    #     install_prefix = os.path.join(self.build_folder, "sis", "prefix")

    #     with tools.chdir(install_prefix):
    #         if self.settings.os == "Windows":
    #             assert len(list(glob.glob(os.path.join("bin", "*.dll")))) > 0
    #         elif tools.is_apple_os(self.settings.os):
    #             assert len(list(glob.glob(os.path.join("lib", "*.dylib")))) > 0
    #         else:
    #             assert len(list(glob.glob(os.path.join("lib", "*.so")))) > 0

    def build(self):

        autotools = Autotools(self)
        autotools.autoreconf()
        autotools.configure()
        autotools.make()

        # self._build_ltdl()
        # if not tools.cross_building(self):
        #     self._build_autotools()
        #     self._build_static_lib_in_shared()

    def test(self):
        pass
        # self._test_ltdl()
        # if not tools.cross_building(self):
        #     self._test_autotools()
        #     self._test_static_lib_in_shared()

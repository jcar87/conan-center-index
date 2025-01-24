import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import copy, get, rmdir, save
from conan.tools.scm import Version

required_conan_version = ">=2.0.9"


class QtADS(ConanFile):
    name = "qt-advanced-docking-system"
    description = (
        "Qt Advanced Docking System lets you create customizable layouts "
        "using a full featured window docking system similar to what is found "
        "in many popular integrated development environments (IDEs) such as "
        "Visual Studio."
    )
    license = "LGPL-2.1-or-later"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/githubuser0xFFFF/Qt-Advanced-Docking-System"
    topics = ("qt", "gui")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]

    @property
    def _qt_major(self):
        return Version(self.dependencies["qt"].ref.version).major

    @property
    def _min_cppstd(self):
        if self._qt_major >= 6:
            return 17
        else:
            return 14

    def export_sources(self):
        copy(self, "moc.sh", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))
        copy(self, "rcc.sh", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))
        copy(self, "qt_tools_macos_rpath_workaround.cmake", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("qt/[>=5.15 <7]", transitive_headers=True)

    def validate(self):
        check_min_cppstd(self, self._min_cppstd)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # VirtualRunEnv is needed to find Qt rcc and Qt moc (when Qt is shared)
        env = VirtualRunEnv(self)
        env.generate(scope="build")

        tc = CMakeToolchain(self)
        tc.cache_variables["ADS_VERSION"] = self.version
        tc.cache_variables["BUILD_EXAMPLES"] = "OFF"
        tc.cache_variables["BUILD_STATIC"] = not self.options.shared
        # https://github.com/githubuser0xFFFF/Qt-Advanced-Docking-System/blob/a16d17a8bf375127847ac8f40af1ebcdb841b13c/src/CMakeLists.txt#L12
        # TODO: the upstream Qt recipe should expose this variable
        qt_version = str(self.dependencies["qt"].ref.version)
        qt_include_root = self.dependencies["qt"].cpp_info.includedirs[0]
        self.output.warning(f"qt major: {self._qt_major}")
        tc.cache_variables[f"Qt6Gui_PRIVATE_INCLUDE_DIRS"] = os.path.join(qt_include_root, "QtGui", qt_version, "QtGui")
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()
        env = Environment()
        env.define("MOC", os.path.join(self.dependencies["qt"].package_folder, "libexec", "moc"))
        env.define("RCC", os.path.join(self.dependencies["qt"].package_folder, "libexec", "rcc"))
        env.vars(self).save_script("conanbuild_qt_tools")
        

    def build(self):
        if self.settings_build.os and self.settings.os == "Macos":
            save(self, os.path.join(self.source_folder, "src", "CMakeLists.txt"), 'include("${CMAKE_SOURCE_DIR}/qt_tools_macos_rpath_workaround.cmake")', append=True)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "gnu-lgpl-v2.1.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        rmdir(self, os.path.join(self.package_folder, "license"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        if Version(self.version) >= 4:
            name = f"qt{self._qt_major}advanceddocking"
            self.cpp_info.includedirs.append(os.path.join("include", name))
            lib_name = f"{name}d" if self.settings.build_type == "Debug" else name
        else:
            lib_name = "qtadvanceddocking"

        self.cpp_info.set_property("cmake_file_name", lib_name)
        self.cpp_info.set_property("cmake_target_name", f"ads::{lib_name}")

        if self.options.shared:
            self.cpp_info.libs = [lib_name]
        else:
            self.cpp_info.defines.append("ADS_STATIC")
            self.cpp_info.libs = [f"{lib_name}_static"]

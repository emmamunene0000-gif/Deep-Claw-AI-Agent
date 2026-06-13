{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.setuptools
    pkgs.gcc
    pkgs.stdenv.cc.cc.lib
  ];
}

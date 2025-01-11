{pkgs}: {
  deps = [
    pkgs.libxcrypt
    pkgs.bash
    pkgs.glibcLocales
    pkgs.postgresql
    pkgs.openssl
  ];
}

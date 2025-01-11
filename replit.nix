{pkgs}: {
  deps = [
    pkgs.openssh
    pkgs.bash
    pkgs.glibcLocales
    pkgs.postgresql
    pkgs.openssl
  ];
}

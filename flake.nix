{
  description = "Collegium OCR microservice";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      nativeLibs = with pkgs; [
        stdenv.cc.cc.lib
        zlib
        glib
        libGL
        libx11
        libxcb
        libxext
        libsm
        libice
      ];
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        packages = [ pkgs.python312 pkgs.uv ] ++ nativeLibs;
        shellHook = ''
          export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath nativeLibs}:$LD_LIBRARY_PATH
          export UV_PYTHON=${pkgs.python312}/bin/python3.12
        '';
      };
    };
}

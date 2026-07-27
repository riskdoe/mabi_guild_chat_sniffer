{
  outputs = { self, nixpkgs }:
  {
    packages.x86_64-linux = let
      pkgs = nixpkgs.legacyPackages.x86_64-linux;
      deps = ps: with ps; [
        python-dotenv
        pyshark
        discord-webhook
        discordpy
      ];
    in {
      default = pkgs.runCommand "mabi_guild_chat_sniffer" {
        src = ./.;
      } ''
        unpackPhase
        cd $sourceRoot
        pwd
        ls -l
        mkdir -pv $out/libexec/mabi-sniffer/ $out/bin/
        cp -vr *.py Mabipacket $out/libexec/mabi-sniffer/

        cat <<EOF > $out/bin/mabi-sniffer
        #!/bin/bash

        export PATH=${pkgs.python3.withPackages deps}/bin:${pkgs.xdotool}/bin:\$PATH

        python $out/libexec/mabi-sniffer/main.py
        EOF

        chmod +x $out/bin/mabi-sniffer

        patchShebangs $out/bin/
      '';
    };
  };
}

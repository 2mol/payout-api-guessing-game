# Edit this configuration file to define what should be installed on
# your system.  Help is available in the configuration.nix(5) man page
# and in the NixOS manual (accessible by running 'nixos-help').

{ config, pkgs, ... }:

let
  fetchKeys = username:
    (builtins.fetchurl "https://github.com/${username}.keys");
in {
  imports =
    [ # Include the results of the hardware scan.
      ./hardware-configuration.nix
      ./vim.nix
    ];

  # Use the GRUB 2 boot loader.
  boot.loader.grub.enable = true;
  boot.loader.grub.version = 2;
  # boot.loader.grub.efiSupport = true;
  # boot.loader.grub.efiInstallAsRemovable = true;
  # boot.loader.efi.efiSysMountPoint = "/boot/efi";
  # Define on which hard drive you want to install Grub.
  # boot.loader.grub.device = "/dev/sda"; # or "nodev" for efi only

  networking.hostName = "bakdor"; # Define your hostname.
  # Pick only one of the below networking options.
  # networking.wireless.enable = true;  # Enables wireless support via wpa_supplicant.
  # networking.networkmanager.enable = true;  # Easiest to use and most distros use this by default.

  # Set your time zone.
  time.timeZone = "Europe/Amsterdam";

  # Configure network proxy if necessary
  # networking.proxy.default = "http://user:password@proxy:port/";
  # networking.proxy.noProxy = "127.0.0.1,localhost,internal.domain";

  # Select internationalisation properties.
  i18n.defaultLocale = "en_US.UTF-8";
  # console = {
  #   font = "Lat2-Terminus16";
  #   keyMap = "us";
  #   useXkbConfig = true; # use xkbOptions in tty.
  # };

  users.users.juri = {
    isNormalUser = true;
    shell = pkgs.zsh;
    extraGroups = [ "wheel" ]; # Enable 'sudo' for the user.
    openssh.authorizedKeys.keys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIsTKysbGk+ALtJbIOaBNmJVWLN91xLEG6VXmlYsp6UO 2mol"
    ];
    packages = with pkgs; [
      # Basics:
      git tmux htop wget
      fd fzf ripgrep
      direnv nix-direnv
      # Networking:
      fail2ban tailscale
      caddy
      # Coding
      python3
    ];
  };

  security.sudo.wheelNeedsPassword = false;

  # List packages installed in system profile. To search, run:
  # $ nix search wget
  environment.systemPackages = with pkgs; [
    neovim
  ];

  nixpkgs.config.allowUnfree = true;

  programs.tmux.extraConfig = ''
    set -g mouse on
    trigger copy mode bybind -n M-Up copy-mode
  '';

  # zsh
  programs.zsh = {
    enable = true;
    shellAliases = {
      sudo = "sudo ";
    };
    promptInit = ""; # otherwise it'll override the grml prompt
    interactiveShellInit = ''
      source ${pkgs.grml-zsh-config}/etc/zsh/zshrc
      if command -v fzf-share >/dev/null; then
        source "$(fzf-share)/key-bindings.zsh"
        source "$(fzf-share)/completion.zsh"
      fi
      eval "$(direnv hook zsh)"
    '';
  };


  # List services that you want to enable:
  services.tailscale.enable = true;
  services.fail2ban.enable = true;
  services.caddy = {
    enable = true;
    globalConfig = ''
      auto_https disable_redirects
    '';
    extraConfig = ''
      bakdor.com {
        respond "Hi there"
      }
      quiz.bakdor.com, http://quiz.bakdor.com {
        encode zstd gzip
        reverse_proxy 127.0.0.1:8000
      }
    '';
  };

  networking.firewall = {
    enable = true;

    # always allow traffic from your Tailscale network
    trustedInterfaces = [ "tailscale0" ];

    # allow the Tailscale UDP port through the firewall
    allowedUDPPorts = [ config.services.tailscale.port ];

    allowedTCPPorts = [ 80 443 ];

    # Tailscale wants this:
    checkReversePath = "loose";
  };


  # This value determines the NixOS release from which the default
  # settings for stateful data, like file locations and database versions
  # on your system were taken. It's perfectly fine and recommended to leave
  # this value at the release version of the first install of this system.
  # Before changing this value read the documentation for this option
  # (e.g. man configuration.nix or on https://nixos.org/nixos/options.html).
  system.stateVersion = "22.05"; # Did you read the comment?


  boot.loader.grub.devices = [ "/dev/sda" ];

  # Initial empty root password for easy login:
  users.users.root.initialHashedPassword = "";
  services.openssh.permitRootLogin = "prohibit-password";

  services.openssh.enable = true;

  users.users.root.openssh.authorizedKeys.keys = [
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIsTKysbGk+ALtJbIOaBNmJVWLN91xLEG6VXmlYsp6UO 2mol"
  ];
}

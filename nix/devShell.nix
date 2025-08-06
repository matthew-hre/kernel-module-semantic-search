{
  mkShell,
  python3,
}:
mkShell {
  name = "semantic-kernel-module-search";

  packages = [
    (python3.withPackages (ps:
      with ps; [
        textual
        sentence-transformers
        faiss
      ]))
  ];
}

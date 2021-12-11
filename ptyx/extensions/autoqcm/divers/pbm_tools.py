# Attention, l'image doit être placée dans le même répertoire
# que votre programme python.


def lire_image(nom_image):
    """Cette fonction prend en argument le nom d'une image PBM
    et renvoie une matrice (c-à-d. une grille) de 0 et de 1
    correspondant à cette image."""
    with open(nom_image) as f:
        contenu = f.read()
    # On saute les lignes de commentaires (commençant par #).
    lignes = [l for l in contenu.split("\n") if not l.startswith("#")]
    # La 1re ligne contient le nbr magique P1.
    if lignes[0] != "P1":
        print("Format d'image incorrect !")
    # La 2e ligne contient les dimensions de l'image.
    l, h = lignes[1].split()
    print("L'image a pour largeur " + l + " et pour hauteur " + h)
    l = int(l)
    h = int(h)
    # Les lignes suivantes contiennent les données.
    matrice = [[]]
    for ligne in lignes[2:]:
        for caractere in ligne:
            # On ne tient pas compte des espaces, etc.
            if caractere in "01":
                # Si on a atteint la largeur de l'image,
                # on commence une nouvelle ligne.
                if len(matrice[-1]) == l:
                    matrice.append([])
                matrice[-1].append(int(caractere))
    print((len(matrice), len(matrice[-1])))
    if len(matrice) != h or len(matrice[-1]) != l:
        print("Les dimensions de l'image ne correspondent pas au contenu !")
    return matrice


def affiche_matrice(matrice):
    """Affiche une matrice (c-à-d. une grille) de manière
    plus lisible qu'avec un simple `print()`."""
    largeur_max = max(max(len(str(val)) for val in ligne) for ligne in matrice)
    for ligne in matrice:
        print("|" + "".join(str(elt).ljust(largeur_max + 2, " ") for elt in ligne)[:-2] + "|")


def sauvegarder_image(nom_image, matrice):
    """Crée une image PBM de nom donné à partir de
    la matrice passée en paramètre."""
    # On récupère les dimensions de l'image.
    h = len(matrice)
    l = len(matrice[0])
    # On ouvre le fichier en mode écriture ("w").
    with open(nom_image, "w") as f:
        f.write("P1\n")
        f.write(str(l) + " " + str(h) + "\n")
        for liste in matrice:
            for valeur in liste:
                f.write(str(valeur))
            f.write("\n")


def echanger_1_0(matrice):
    """Modifie la matrice en remplaçant les 1 par des 0
    et les 0 par des 1."""
    nbr_lignes = len(matrice)
    # Pour trouver le nombre de colonnes, on prend la
    # longueur de la 1re ligne (par exemple).
    nbr_colonnes = len(matrice[0])
    # On fait varier le numéro i de la ligne,
    # et le numéro j de la colonne.
    for i in range(nbr_lignes):
        for j in range(nbr_colonnes):
            # Rajouter ici votre code de manière à ce que
            # tous les 1 deviennent des 0 et tous les 0
            # des 1.
            pass
    return matrice


# affiche_grille(lire_image("smiley.pbm"))

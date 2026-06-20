import matplotlib.pyplot as plt


def plot_far_frr(
    thresholds,
    fars,
    frrs
):

    plt.figure(figsize=(8, 5))

    plt.plot(
        thresholds,
        fars,
        label="FAR"
    )

    plt.plot(
        thresholds,
        frrs,
        label="FRR"
    )

    plt.xlabel("Threshold")

    plt.ylabel("Rate")

    plt.legend()

    plt.grid()

    plt.show()
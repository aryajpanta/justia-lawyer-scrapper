import csv
from typing import List
from .schema import Lawyer


def write_lawyers_to_csv(
    lawyers: List[Lawyer], output_path: str = "immigration_lawyers.csv"
) -> None:
    """
    Write list of Lawyer objects to a CSV file.

    Args:
        lawyers: List of Lawyer objects to write
        output_path: Path to output CSV file (default: immigration_lawyers.csv)
    """
    fieldnames = ["Name", "Phone", "Address", "Profile_URL", "Bio_Experience"]

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for lawyer in lawyers:
            writer.writerow(
                {
                    "Name": lawyer.Name,
                    "Phone": lawyer.Phone or "",
                    "Address": lawyer.Address or "",
                    "Profile_URL": lawyer.Profile_URL,
                    "Bio_Experience": lawyer.Bio_Experience or "",
                }
            )

    if lawyers:
        print(f"Successfully wrote {len(lawyers)} lawyers to {output_path}")
    else:
        print("Warning: No lawyer data extracted; CSV contains only headers")

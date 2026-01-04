from bs4 import BeautifulSoup
from bs4.element import Tag
import re
from typing import Optional, Union


def tettorosso_extract_from_table(
    table: Tag, field_name: str, is_number: bool
) -> Union[str, int, None]:
    """
    Extract data from a property table in Tettorosso website

    Args:
        table: BeautifulSoup Tag object containing the table
        field_name: Name of the field to extract
        is_number: Whether to extract as number or string

    Returns:
        Extracted value as string or int, or empty string if not found
    """
    if not table:
        return None

    field_text = table.find(text=field_name)
    if not field_text:
        return None

    # Navigate to the value cell
    parent = field_text.parent
    if not parent:
        return None

    grandparent = parent.parent
    if not grandparent:
        return None

    great_grandparent = grandparent.parent
    if not great_grandparent:
        return None

    children = list(great_grandparent.children)
    if len(children) != 5:
        return None

    child = children[3]
    if not child:
        return None

    if is_number:
        m = re.search(r"[^0-9]*([0-9\.]+)[^0-9]*", child.text)
        if m:
            return int(m.group(1).replace(".", ""))
    else:
        return child.text.strip() if child.text else None

    return None


if __name__ == "__main__":
    with open("example.html", "r") as file:
        data = file.read()
        soup = BeautifulSoup(data, "html.parser")
        tabella = soup.find(id="caratt")
        if tabella:
            tabella = tabella.find(class_="property-d-table")
            if tabella:
                tabella = tabella.find("tbody")

        print("-----------------------------")
        print(tabella)
        print("-----------------------------")

        if tabella:
            prezzo = tettorosso_extract_from_table(
                table=tabella, field_name="Prezzo", is_number=True
            )
            anno = tettorosso_extract_from_table(
                table=tabella, field_name="Anno di costruzione", is_number=True
            )
            piano = tettorosso_extract_from_table(
                table=tabella, field_name="Piano", is_number=False
            )

            print(f"Prezzo: {prezzo}")
            print(f"Anno di costruzione: {anno}")
            print(f"Piano: {piano}")

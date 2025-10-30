"""
Hardware Abstraction Layer (HAL) for PC/SC NFC Readers.

This module provides a high-level interface to smart card readers
supported by the PC/SC standard. It abstracts away the low-level
details of the pyscard library.
"""

from ntag424_sdm_provisioner.hal import CardManager, NoReadersError

def list_readers() -> list[str]:
    """
    Retrieves a list of all available PC/SC smart card readers.

    Returns:
        A list of strings, where each string is the name of a connected reader.

    Raises:
        NoReadersError: If no PC/SC readers are found on the system.
    """
    with CardManager() as cm:
        readers = cm.list_readers()
        if not readers:
            raise NoReadersError("No PC/SC readers found.")
        return readers  

if __name__ == '__main__':
    # Example usage: a simple discovery script.
    print("Searching for available PC/SC readers...")
    try:
        reader_list = list_readers()
        if reader_list:
            print("Found readers:")
            for i, reader in enumerate(reader_list):
                print(f"  [{i}]: {reader}")
        # The case where no readers are found is handled inside the function.
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
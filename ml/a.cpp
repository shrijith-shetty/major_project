#include <iostream>
#include <fstream>
#include <vector>
#include <string>
using namespace std;

int main()
{
    string filename;
    cout << "Enter file name: ";
    getline(cin, filename); // ✅ Get filename from user

    ifstream file(filename); // ✅ Open file
    if (!file) {
        cout << "Error opening file!" << endl;
        return 1; // exit if file not found
    }

    vector<string> lines;
    string line;

    // ✅ Read each line from file and store in vector
    while (getline(file, line)) {
        lines.push_back(line);
    }

    file.close();

    // ✅ Print file content in reverse order
    cout << "\nFile content in reverse:\n";
    for (int i = lines.size() - 1; i >= 0; --i) {
        cout << lines[i] << endl;
    }

    return 0;
}

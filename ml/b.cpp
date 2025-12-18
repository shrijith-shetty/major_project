#include<iostream>
#include<fstream>
#include<string>
#include<vector>
using namespace std;

int main()
{
    string fil;
    cout<<"Enter the file name:";
    getline(cin, fil);

    ifstream file(fil);
    if(!file)
        cout<<"errro";
    else{
        vector<string> vec;
        string line;
        while(getline(file, line))
        {
            vec.push_back(line);
        }
        file.close();
        for(auto a : vec)
        {
            cout<<a<<endl;
        }
    }

}
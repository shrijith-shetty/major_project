#include <iostream>
using namespace std;

class Node
{
public:
    int data;
    Node *next;

    Node(int val)
    {
        data = val;
        next = nullptr;
    }
};

class Stack
{
private:
    Node *top;

public:
    Stack()
    {
        top = nullptr;
    }

    void push(int val)
    {

        Node *newnode = new Node(val);
        newnode->next = top;
        top = newnode;
        cout << top->data << "Pushed into the stack" << endl;
    }

    void pop()
    {
        if (isEmpty())
        {
            cout << "IsEmpty" << endl;
            return;
        }
        Node *tmp = top;
        top = top->next;
        cout << tmp->data << " is deleted" << endl;
        delete tmp;
    }

    bool isEmpty()
    {
        return top == nullptr;
    }

    void peek()
    {
        if (isEmpty())
        {
            cout << "IsEmpty" << endl;
            return;
        }
        cout <<"top data is "<<top->data<<endl;
    }

    void display()
    {
        if(isEmpty())
        {
            cout<<"IsEmpty"<<endl;
            return;
        }
        Node *tmp = top;
        while(tmp!=nullptr)
        {
            cout<<tmp->data<<" ";
            tmp = tmp->next;
        }
        cout<<endl;
    }
};
int main()
{
    Stack s;
    s.push(10);
    s.push(20);
    s.push(30);
    s.display();
    s.peek();
    s.pop();
    s.display();
    return 0;
}
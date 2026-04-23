/*
 * ============================================================
 *    LibraryPro — Advanced C++ Backend Engine.
 *    Data Structures Used:
 *    • Singly Linked List   :— core book catalog
 *    • HashMap (unordered_map) :— O(1) book lookup
 *    • Stack                :— recent returns history
 *    • Queue                :— standard waiting list
 *    • Priority Queue       :— VIP / faculty priority queue
 *    • Binary Search Tree   :— sorted book display by title
 *    • Adjacency-List Graph :— book recommendation engine
 * ============================================================
 */

#include <iostream>
#include <fstream>
#include <sstream>
#include <unordered_map>
#include <map>
#include <stack>
#include <queue>
#include <vector>
#include <algorithm>
#include <set>
#include <ctime>
using namespace std;

// ─────────────────────────────────────────────
// DATA STRUCTURES
// ─────────────────────────────────────────────

/* Core book node for singly linked list */
struct Book {
    int    id;
    string title;
    string author;
    string category;
    int    issued;        // 0 = available, 1 = issued
    string student_name;
    string student_id;
    string due_date;      // YYYY-MM-DD
    int    vip;           // 1 = VIP/faculty, 0 = regular
    Book*  next;
};

/* BST node — stores books sorted by title */
struct BSTNode {
    int    book_id;
    string title;
    BSTNode* left;
    BSTNode* right;
    BSTNode(int id, string t) : book_id(id), title(t), left(nullptr), right(nullptr) {}
};

/* Priority Queue entry — for VIP waiting list */
struct WaitEntry {
    int  book_id;
    int  priority;   // lower number = higher priority (VIP=1, Regular=2)
    string student_name;
    string student_id;

    // Min-heap: smaller priority number pops first
    bool operator>(const WaitEntry& o) const { return priority > o.priority; }
};

// ─────────────────────────────────────────────
// GLOBALS
// ─────────────────────────────────────────────
Book* head = nullptr;
unordered_map<int, Book*>            bookMap;      // HashMap: id → Book*
stack<pair<int,string>>              returnStack;  // (book_id, title)
queue<pair<int,string>>              waitQueue;    // standard FIFO queue
priority_queue<WaitEntry,
    vector<WaitEntry>,
    greater<WaitEntry>>              vipQueue;     // priority queue

// BST root
BSTNode* bstRoot = nullptr;

// Graph: book_id → list of related book_ids (recommendation graph)
unordered_map<int, vector<int>>      recGraph;
// Category index: category → list of book_ids
unordered_map<string, vector<int>>   categoryIndex;
// Author index: author → list of book_ids
unordered_map<string, vector<int>>   authorIndex;

// ─────────────────────────────────────────────
// BST OPERATIONS
// ─────────────────────────────────────────────
BSTNode* bstInsert(BSTNode* root, int id, const string& title) {
    if (!root) return new BSTNode(id, title);
    if (title < root->title)
        root->left  = bstInsert(root->left,  id, title);
    else
        root->right = bstInsert(root->right, id, title);
    return root;
}

/* In-order traversal → sorted book list */
void bstInOrder(BSTNode* root) {
    if (!root) return;
    bstInOrder(root->left);
    if (bookMap.count(root->book_id)) {
        Book* b = bookMap[root->book_id];
        cout << b->id << "|" << b->title << "|" << b->author
             << "|" << b->category << "|" << b->issued
             << "|" << b->student_name << "|" << b->student_id
             << "|" << b->due_date << "|" << b->vip << "\n";
    }
    bstInOrder(root->right);
}

BSTNode* bstDelete(BSTNode* root, const string& title) {
    if (!root) return nullptr;
    if (title < root->title)      root->left  = bstDelete(root->left,  title);
    else if (title > root->title) root->right = bstDelete(root->right, title);
    else {
        if (!root->left)  { BSTNode* r = root->right; delete root; return r; }
        if (!root->right) { BSTNode* l = root->left;  delete root; return l; }
        BSTNode* succ = root->right;
        while (succ->left) succ = succ->left;
        root->title   = succ->title;
        root->book_id = succ->book_id;
        root->right   = bstDelete(root->right, succ->title);
    }
    return root;
}

// ─────────────────────────────────────────────
// GRAPH: BUILD RECOMMENDATION EDGES
// Edges: same author OR same category → recommend each other
// ─────────────────────────────────────────────
void buildRecommendationGraph() {
    recGraph.clear();
    // BY categoryv

    // By category
    for (auto& [cat, ids] : categoryIndex)
        for (int a : ids)
            for (int b : ids)
                if (a != b) recGraph[a].push_back(b);

    // By author
    for (auto& [author, ids] : authorIndex)
        for (int a : ids)
            for (int b : ids)
                if (a != b) recGraph[a].push_back(b);

    // Deduplicate neighbour lists
    for (auto& [id, neighbours] : recGraph) {
        sort(neighbours.begin(), neighbours.end());
        neighbours.erase(unique(neighbours.begin(), neighbours.end()), neighbours.end());
    }
}

/* BFS-based recommendation: returns up to `limit` book_ids */
void getRecommendations(int book_id, int limit) {
    if (!recGraph.count(book_id)) { cout << "NONE\n"; return; }

    set<int> visited;
    queue<int> bfsQ;
    visited.insert(book_id);
    bfsQ.push(book_id);
    int count = 0;

    while (!bfsQ.empty() && count < limit) {
        int cur = bfsQ.front(); bfsQ.pop();
        for (int nb : recGraph[cur]) {
            if (!visited.count(nb)) {
                visited.insert(nb);
                bfsQ.push(nb);
                if (bookMap.count(nb)) {
                    Book* b = bookMap[nb];
                    cout << b->id << "|" << b->title << "|"
                         << b->author << "|" << b->category << "\n";
                    count++;
                    if (count >= limit) break;
                }
            }
        }
    }
    if (count == 0) cout << "NONE\n";
}

// ─────────────────────────────────────────────
// HELPER: Append book to Linked List tail
// ─────────────────────────────────────────────
void appendToList(Book* b) {
    if (!head) { head = b; return; }
    Book* temp = head;
    while (temp->next) temp = temp->next;
    temp->next = b;
}

// ─────────────────────────────────────────────
// LOAD — pipe-delimited for safety
// ─────────────────────────────────────────────
void loadData(const string& path) {
    ifstream file(path);
    if (!file.is_open()) return;
    string line;

    while (getline(file, line)) {
        if (line.empty()) continue;
        stringstream ss(line);
        string tok[9];
        for (int i = 0; i < 9; i++) getline(ss, tok[i], '|');

        Book* b   = new Book();
        b->id           = stoi(tok[0]);
        b->title        = tok[1];
        b->author       = tok[2];
        b->category     = tok[3];
        b->issued       = stoi(tok[4]);
        b->student_name = tok[5];
        b->student_id   = tok[6];
        b->due_date     = tok[7];
        b->vip          = (tok[8] == "1") ? 1 : 0;
        b->next         = nullptr;

        appendToList(b);
        bookMap[b->id] = b;

        // Index for graph
        categoryIndex[b->category].push_back(b->id);
        authorIndex[b->author].push_back(b->id);

        // Insert into BST
        bstRoot = bstInsert(bstRoot, b->id, b->title);
    }

    buildRecommendationGraph();
}

// ─────────────────────────────────────────────
// SAVE
// ─────────────────────────────────────────────
void saveData(const string& path) {
    ofstream file(path);
    Book* temp = head;
    while (temp) {
        file << temp->id       << "|"
             << temp->title    << "|"
             << temp->author   << "|"
             << temp->category << "|"
             << temp->issued   << "|"
             << temp->student_name << "|"
             << temp->student_id   << "|"
             << temp->due_date     << "|"
             << temp->vip          << "\n";
        temp = temp->next;
    }
}

// ─────────────────────────────────────────────
// ADD BOOK
// ─────────────────────────────────────────────
void addBook(const string& path, int id, const string& title,
             const string& author, const string& category) {
    if (bookMap.count(id)) {
        cout << "ERROR:ID_EXISTS\n"; return;
    }
    Book* b = new Book{id, title, author, category,
                       0, "-", "-", "-", 0, nullptr};
    appendToList(b);
    bookMap[id] = b;

    categoryIndex[category].push_back(id);
    authorIndex[author].push_back(id);
    bstRoot = bstInsert(bstRoot, id, title);
    buildRecommendationGraph();

    saveData(path);
    cout << "OK\n";
}

// ─────────────────────────────────────────────
// DISPLAY (sorted via BST in-order)
// ─────────────────────────────────────────────
void displayBooks() { bstInOrder(bstRoot); }

// ─────────────────────────────────────────────
// ISSUE BOOK
// ─────────────────────────────────────────────
void issueBook(const string& path, int id,
               const string& student, const string& sid,
               const string& due_date, int vip_flag) {
    if (!bookMap.count(id)) { cout << "ERROR:NOT_FOUND\n"; return; }

    Book* b = bookMap[id];
    if (b->issued == 0) {
        b->issued       = 1;
        b->student_name = student;
        b->student_id   = sid;
        b->due_date     = due_date;
        b->vip          = vip_flag;
        saveData(path);
        cout << "OK:ISSUED\n";
    } else {
        // Add to priority queue
        WaitEntry e{id, vip_flag == 1 ? 1 : 2, student, sid};
        vipQueue.push(e);
        waitQueue.push({id, student});
        saveData(path);
        cout << "OK:QUEUED\n";
    }
}

// ─────────────────────────────────────────────
// RETURN BOOK — auto-assigns to next in queue
// ─────────────────────────────────────────────
void returnBook(const string& path, int id, const string& return_date) {
    if (!bookMap.count(id)) { cout << "ERROR:NOT_FOUND\n"; return; }

    Book* b = bookMap[id];
    if (b->issued == 0) { cout << "ERROR:NOT_ISSUED\n"; return; }

    // Push to return history stack
    returnStack.push({id, b->title});

    // Auto-assign: check priority queue first
    bool assigned = false;
    while (!vipQueue.empty()) {
        WaitEntry e = vipQueue.top(); vipQueue.pop();
        if (e.book_id == id) {
            b->student_name = e.student_name;
            b->student_id   = e.student_id;
            b->vip          = e.priority == 1 ? 1 : 0;
            // Set new due date 14 days from return
            b->due_date = return_date; // Flask layer adds 14 days
            assigned = true;
            cout << "OK:AUTO_ASSIGNED:" << e.student_name << "\n";
            break;
        }
    }

    if (!assigned) {
        b->issued       = 0;
        b->student_name = "-";
        b->student_id   = "-";
        b->due_date     = "-";
        b->vip          = 0;
        cout << "OK:RETURNED\n";
    }

    saveData(path);
}

// ─────────────────────────────────────────────
// DELETE BOOK
// ─────────────────────────────────────────────
void deleteBook(const string& path, int id) {
    if (!bookMap.count(id)) { cout << "ERROR:NOT_FOUND\n"; return; }

    Book* b    = bookMap[id];
    string title = b->title;

    // Remove from linked list
    Book* temp = head; Book* prev = nullptr;
    while (temp) {
        if (temp->id == id) {
            if (prev) prev->next = temp->next;
            else      head       = temp->next;
            break;
        }
        prev = temp; temp = temp->next;
    }

    // Remove from indexes
    bookMap.erase(id);
    bstRoot = bstDelete(bstRoot, title);

    auto rm = [&](vector<int>& v) {
        v.erase(remove(v.begin(), v.end(), id), v.end());
    };
    rm(categoryIndex[b->category]);
    rm(authorIndex[b->author]);

    delete b;
    buildRecommendationGraph();
    saveData(path);
    cout << "OK\n";
}

// ─────────────────────────────────────────────
// SEARCH by title or author (partial match)
// ─────────────────────────────────────────────
void searchBooks(const string& query) {
    string q = query;
    transform(q.begin(), q.end(), q.begin(), ::tolower);
    bool found = false;
    Book* temp = head;
    while (temp) {
        string t = temp->title, a = temp->author;
        transform(t.begin(), t.end(), t.begin(), ::tolower);
        transform(a.begin(), a.end(), a.begin(), ::tolower);
        if (t.find(q) != string::npos || a.find(q) != string::npos) {
            cout << temp->id << "|" << temp->title << "|" << temp->author
                 << "|" << temp->category << "|" << temp->issued
                 << "|" << temp->student_name << "|" << temp->student_id
                 << "|" << temp->due_date << "|" << temp->vip << "\n";
            found = true;
        }
        temp = temp->next;
    }
    if (!found) cout << "NONE\n";
}

// ─────────────────────────────────────────────
// SHOW QUEUE
// ─────────────────────────────────────────────
void showQueue() {
    // Show priority queue (VIP first)
    priority_queue<WaitEntry, vector<WaitEntry>, greater<WaitEntry>> tmp = vipQueue;
    if (tmp.empty()) { cout << "EMPTY\n"; return; }
    while (!tmp.empty()) {
        WaitEntry e = tmp.top(); tmp.pop();
        string type = (e.priority == 1) ? "VIP" : "Regular";
        cout << e.book_id << "|" << e.student_name << "|" << e.student_id
             << "|" << type << "\n";
    }
}

// ─────────────────────────────────────────────
// SHOW STACK (recent returns)
// ─────────────────────────────────────────────
void showStack() {
    stack<pair<int,string>> tmp = returnStack;
    if (tmp.empty()) { cout << "EMPTY\n"; return; }
    while (!tmp.empty()) {
        cout << tmp.top().first << "|" << tmp.top().second << "\n";
        tmp.pop();
    }
}

// ─────────────────────────────────────────────
// STATS
// ─────────────────────────────────────────────
void showStats() {
    int total = 0, issued = 0, avail = 0;
    map<string, int> catCount;
    Book* temp = head;
    while (temp) {
        total++;
        if (temp->issued) { issued++; catCount[temp->category]++; }
        else avail++;
        temp = temp->next;
    }
    cout << "TOTAL:" << total << "\n"
         << "ISSUED:" << issued << "\n"
         << "AVAILABLE:" << avail << "\n";
    for (auto& [cat, cnt] : catCount)
        cout << "CAT:" << cat << ":" << cnt << "\n";
}

// ─────────────────────────────────────────────
// RECOMMEND
// ─────────────────────────────────────────────

// ─────────────────────────────────────────────
// MAIN
// ─────────────────────────────────────────────
int main(int argc, char* argv[]) {
    if (argc < 2) { cerr << "No command\n"; return 1; }

    // Default data file location
    string dataFile = "library_data.dat";
    if (argc >= 3 && string(argv[1]) != "add") {
        // data file can be passed as last arg in some commands
    }

    string cmd = argv[1];

    // Most commands need data loaded first
    if (cmd != "help") loadData(dataFile);

    if (cmd == "add" && argc >= 6) {
        addBook(dataFile, stoi(argv[2]), argv[3], argv[4], argv[5]);

    } else if (cmd == "display") {
        displayBooks();

    } else if (cmd == "issue" && argc >= 7) {
        issueBook(dataFile, stoi(argv[2]), argv[3], argv[4], argv[5], stoi(argv[6]));

    } else if (cmd == "return" && argc >= 4) {
        returnBook(dataFile, stoi(argv[2]), argv[3]);

    } else if (cmd == "delete" && argc >= 3) {
        deleteBook(dataFile, stoi(argv[2]));

    } else if (cmd == "search" && argc >= 3) {
        searchBooks(argv[2]);

    } else if (cmd == "recommend" && argc >= 3) {
        int limit = (argc >= 4) ? stoi(argv[3]) : 5;
        getRecommendations(stoi(argv[2]), limit);

    } else if (cmd == "queue") {
        showQueue();

    } else if (cmd == "stack") {
        showStack();

    } else if (cmd == "stats") {
        showStats();

    } else {
        cerr << "Unknown command: " << cmd << "\n";
        return 1;
    }

    return 0;
}

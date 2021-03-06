#include "Record.hpp"
#include "Storage.hpp"

#include <iostream>
#include <sstream>

using namespace std;

void Record::UpdateByVect(std::string vect_name, long long vect_timestamp, std::vector<std::string> vect_value)
{
	bool doUpdate;

	// TODO: Assert that vect_value has at least size 1.

	if(values.count(vect_name)) {
		pair<long long, vector<string>> prev = values[vect_name];

		long long prev_timestamp = prev.first;

		if(prev_timestamp > vect_timestamp) {
			doUpdate = false;
		} else {
			doUpdate = true;
		}
	} else {
		doUpdate = true;
	}

	if(doUpdate) {
		values[vect_name] = std::pair<long long, vector<string>>(vect_timestamp, vect_value);
	}
}

bool Record::IsValid()
{
	return valid;
}

std::map<std::string, std::vector<std::string>> Record::GetFields()
{
	map<string, vector<string>> ret;

	for(map<string, pair<long long, vector<string>>>::value_type &rec_triple : values) {
		const string &field_name = rec_triple.first;
		pair<long long, vector<string>> &field_pair = rec_triple.second;
		//long long field_timestamp = field_pair.first;
		vector<string> &field_value = field_pair.second;

		
		if(field_name.size() < 1 || field_name[0]!='_') {
			// We have found the PATH field, which gets separate treatment: you read it with GetPath().
			continue;
		}


		string field_name_shortened = field_name.substr(1, field_name.size()-1);


		if (ret.count(field_name_shortened)) {
			throw runtime_error("Unexpected duplicate path encountered in Record::GetFields.\n");
		}

		ret[field_name_shortened] = field_value;
	}

	// empty fields have to be removed, else they cause problems later.
	
	map<string, vector<string>>::iterator iter = ret.begin();
	while (iter != ret.end()) {
		
		if (iter->second.size()==0) {
			ret.erase(iter++);  // alternatively, i = items.erase(i);
		} else {
			++iter;
		}
	}
	

	return ret;
}

void Record::PrintRecord()
{
	cout << "\t" << "rid=" << GetId() << "\n";

	for(map<string, vector<string>>::value_type &field : GetFields()) {
		cout << "\t" << field.first << "=(";
		bool first=true;
		for(const string &value : field.second) {
			if(!first) {
				cout << ", ";
			}
			cout << "'" << value << "'"; 

			first=false;
		}
		cout << ")\n";
	}
}

Record::Record()
{
	this->record_id = "INVALID";
	valid = false;
}

Record::Record(std::string record_id)
{
	this->record_id = record_id;
	valid = true;
}

bool Record::IsHidden()
{
	if(values.count("PATH")) {
		if(values["PATH"].second.size()<1 || values["PATH"].second[0].size()<1) {
			return true;
		} else {
			return false;
		}
	} else {
		return true;
	}
}


std::string Record::GetPath()
{
	if(values.count("PATH")) {
		if(values["PATH"].second.size()<1 || values["PATH"].second[0].size()<1) {
			return "@DeletedRecord/"+GetId();
		} else {
			return values["PATH"].second[0];
		}
	} else {
		return "@UnnamedRecord/"+GetId(); //RID="+GetId();
	}
}

std::string Record::GetId()
{
	return record_id;
}

// set dest = NULL to dry run
string Record::SetNewFieldsToStorage(Storage *dest, map<string, vector<string>> &newFields)
{
	stringstream changeSummary;

	map<string, vector<string>> oldFields = GetFields();

	string path = GetPath();

	// Set new fields
    for(auto const &curField : newFields) {
    	if(oldFields.count(curField.first) == 0) {
    		changeSummary << "New field: " << curField.first << endl;
    		if(dest) {
    			dest->RecordSet(path, curField.first, curField.second);
    		}
    	}
    }

	// Update existing fields
    // Set new fields
    for(auto const &curField : newFields) {
    	if(oldFields.count(curField.first) > 0) {
    		if(oldFields[curField.first] != curField.second) {
    			changeSummary << "Changed field: " << curField.first << endl;
    			if(dest) {
    				dest->RecordSet(path, curField.first, curField.second);
    			}
    		} else {
    			//changeSummary << "Unchanged field: " << curField.first << endl;
    		}
    	}
    }

	// Delete old fields
	for(auto const &curField : oldFields) {
		if(newFields.count(curField.first) == 0) {
			changeSummary << "Deleted field: " << curField.first << endl;
			if(dest) {
				dest->RecordUnset(path, curField.first);
			}
		}
	}

	return changeSummary.str();
}
#pragma once
#include <string>
class StringUtils
{
public:
    static std::string wchar_to_string(const wchar_t* value)
    {
        std::string text;
        while(*value) text.push_back((char)*value++);
        return text;
    }
};

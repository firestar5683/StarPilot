#include "pose.h"

namespace {
#define DIM 18
#define EDIM 18
#define MEDIM 18
typedef void (*Hfun)(double *, double *, double *);
const static double MAHA_THRESH_4 = 7.814727903251177;
const static double MAHA_THRESH_10 = 7.814727903251177;
const static double MAHA_THRESH_13 = 7.814727903251177;
const static double MAHA_THRESH_14 = 7.814727903251177;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_7825504593440143444) {
   out_7825504593440143444[0] = delta_x[0] + nom_x[0];
   out_7825504593440143444[1] = delta_x[1] + nom_x[1];
   out_7825504593440143444[2] = delta_x[2] + nom_x[2];
   out_7825504593440143444[3] = delta_x[3] + nom_x[3];
   out_7825504593440143444[4] = delta_x[4] + nom_x[4];
   out_7825504593440143444[5] = delta_x[5] + nom_x[5];
   out_7825504593440143444[6] = delta_x[6] + nom_x[6];
   out_7825504593440143444[7] = delta_x[7] + nom_x[7];
   out_7825504593440143444[8] = delta_x[8] + nom_x[8];
   out_7825504593440143444[9] = delta_x[9] + nom_x[9];
   out_7825504593440143444[10] = delta_x[10] + nom_x[10];
   out_7825504593440143444[11] = delta_x[11] + nom_x[11];
   out_7825504593440143444[12] = delta_x[12] + nom_x[12];
   out_7825504593440143444[13] = delta_x[13] + nom_x[13];
   out_7825504593440143444[14] = delta_x[14] + nom_x[14];
   out_7825504593440143444[15] = delta_x[15] + nom_x[15];
   out_7825504593440143444[16] = delta_x[16] + nom_x[16];
   out_7825504593440143444[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6707226023055995729) {
   out_6707226023055995729[0] = -nom_x[0] + true_x[0];
   out_6707226023055995729[1] = -nom_x[1] + true_x[1];
   out_6707226023055995729[2] = -nom_x[2] + true_x[2];
   out_6707226023055995729[3] = -nom_x[3] + true_x[3];
   out_6707226023055995729[4] = -nom_x[4] + true_x[4];
   out_6707226023055995729[5] = -nom_x[5] + true_x[5];
   out_6707226023055995729[6] = -nom_x[6] + true_x[6];
   out_6707226023055995729[7] = -nom_x[7] + true_x[7];
   out_6707226023055995729[8] = -nom_x[8] + true_x[8];
   out_6707226023055995729[9] = -nom_x[9] + true_x[9];
   out_6707226023055995729[10] = -nom_x[10] + true_x[10];
   out_6707226023055995729[11] = -nom_x[11] + true_x[11];
   out_6707226023055995729[12] = -nom_x[12] + true_x[12];
   out_6707226023055995729[13] = -nom_x[13] + true_x[13];
   out_6707226023055995729[14] = -nom_x[14] + true_x[14];
   out_6707226023055995729[15] = -nom_x[15] + true_x[15];
   out_6707226023055995729[16] = -nom_x[16] + true_x[16];
   out_6707226023055995729[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_4618881527044107692) {
   out_4618881527044107692[0] = 1.0;
   out_4618881527044107692[1] = 0.0;
   out_4618881527044107692[2] = 0.0;
   out_4618881527044107692[3] = 0.0;
   out_4618881527044107692[4] = 0.0;
   out_4618881527044107692[5] = 0.0;
   out_4618881527044107692[6] = 0.0;
   out_4618881527044107692[7] = 0.0;
   out_4618881527044107692[8] = 0.0;
   out_4618881527044107692[9] = 0.0;
   out_4618881527044107692[10] = 0.0;
   out_4618881527044107692[11] = 0.0;
   out_4618881527044107692[12] = 0.0;
   out_4618881527044107692[13] = 0.0;
   out_4618881527044107692[14] = 0.0;
   out_4618881527044107692[15] = 0.0;
   out_4618881527044107692[16] = 0.0;
   out_4618881527044107692[17] = 0.0;
   out_4618881527044107692[18] = 0.0;
   out_4618881527044107692[19] = 1.0;
   out_4618881527044107692[20] = 0.0;
   out_4618881527044107692[21] = 0.0;
   out_4618881527044107692[22] = 0.0;
   out_4618881527044107692[23] = 0.0;
   out_4618881527044107692[24] = 0.0;
   out_4618881527044107692[25] = 0.0;
   out_4618881527044107692[26] = 0.0;
   out_4618881527044107692[27] = 0.0;
   out_4618881527044107692[28] = 0.0;
   out_4618881527044107692[29] = 0.0;
   out_4618881527044107692[30] = 0.0;
   out_4618881527044107692[31] = 0.0;
   out_4618881527044107692[32] = 0.0;
   out_4618881527044107692[33] = 0.0;
   out_4618881527044107692[34] = 0.0;
   out_4618881527044107692[35] = 0.0;
   out_4618881527044107692[36] = 0.0;
   out_4618881527044107692[37] = 0.0;
   out_4618881527044107692[38] = 1.0;
   out_4618881527044107692[39] = 0.0;
   out_4618881527044107692[40] = 0.0;
   out_4618881527044107692[41] = 0.0;
   out_4618881527044107692[42] = 0.0;
   out_4618881527044107692[43] = 0.0;
   out_4618881527044107692[44] = 0.0;
   out_4618881527044107692[45] = 0.0;
   out_4618881527044107692[46] = 0.0;
   out_4618881527044107692[47] = 0.0;
   out_4618881527044107692[48] = 0.0;
   out_4618881527044107692[49] = 0.0;
   out_4618881527044107692[50] = 0.0;
   out_4618881527044107692[51] = 0.0;
   out_4618881527044107692[52] = 0.0;
   out_4618881527044107692[53] = 0.0;
   out_4618881527044107692[54] = 0.0;
   out_4618881527044107692[55] = 0.0;
   out_4618881527044107692[56] = 0.0;
   out_4618881527044107692[57] = 1.0;
   out_4618881527044107692[58] = 0.0;
   out_4618881527044107692[59] = 0.0;
   out_4618881527044107692[60] = 0.0;
   out_4618881527044107692[61] = 0.0;
   out_4618881527044107692[62] = 0.0;
   out_4618881527044107692[63] = 0.0;
   out_4618881527044107692[64] = 0.0;
   out_4618881527044107692[65] = 0.0;
   out_4618881527044107692[66] = 0.0;
   out_4618881527044107692[67] = 0.0;
   out_4618881527044107692[68] = 0.0;
   out_4618881527044107692[69] = 0.0;
   out_4618881527044107692[70] = 0.0;
   out_4618881527044107692[71] = 0.0;
   out_4618881527044107692[72] = 0.0;
   out_4618881527044107692[73] = 0.0;
   out_4618881527044107692[74] = 0.0;
   out_4618881527044107692[75] = 0.0;
   out_4618881527044107692[76] = 1.0;
   out_4618881527044107692[77] = 0.0;
   out_4618881527044107692[78] = 0.0;
   out_4618881527044107692[79] = 0.0;
   out_4618881527044107692[80] = 0.0;
   out_4618881527044107692[81] = 0.0;
   out_4618881527044107692[82] = 0.0;
   out_4618881527044107692[83] = 0.0;
   out_4618881527044107692[84] = 0.0;
   out_4618881527044107692[85] = 0.0;
   out_4618881527044107692[86] = 0.0;
   out_4618881527044107692[87] = 0.0;
   out_4618881527044107692[88] = 0.0;
   out_4618881527044107692[89] = 0.0;
   out_4618881527044107692[90] = 0.0;
   out_4618881527044107692[91] = 0.0;
   out_4618881527044107692[92] = 0.0;
   out_4618881527044107692[93] = 0.0;
   out_4618881527044107692[94] = 0.0;
   out_4618881527044107692[95] = 1.0;
   out_4618881527044107692[96] = 0.0;
   out_4618881527044107692[97] = 0.0;
   out_4618881527044107692[98] = 0.0;
   out_4618881527044107692[99] = 0.0;
   out_4618881527044107692[100] = 0.0;
   out_4618881527044107692[101] = 0.0;
   out_4618881527044107692[102] = 0.0;
   out_4618881527044107692[103] = 0.0;
   out_4618881527044107692[104] = 0.0;
   out_4618881527044107692[105] = 0.0;
   out_4618881527044107692[106] = 0.0;
   out_4618881527044107692[107] = 0.0;
   out_4618881527044107692[108] = 0.0;
   out_4618881527044107692[109] = 0.0;
   out_4618881527044107692[110] = 0.0;
   out_4618881527044107692[111] = 0.0;
   out_4618881527044107692[112] = 0.0;
   out_4618881527044107692[113] = 0.0;
   out_4618881527044107692[114] = 1.0;
   out_4618881527044107692[115] = 0.0;
   out_4618881527044107692[116] = 0.0;
   out_4618881527044107692[117] = 0.0;
   out_4618881527044107692[118] = 0.0;
   out_4618881527044107692[119] = 0.0;
   out_4618881527044107692[120] = 0.0;
   out_4618881527044107692[121] = 0.0;
   out_4618881527044107692[122] = 0.0;
   out_4618881527044107692[123] = 0.0;
   out_4618881527044107692[124] = 0.0;
   out_4618881527044107692[125] = 0.0;
   out_4618881527044107692[126] = 0.0;
   out_4618881527044107692[127] = 0.0;
   out_4618881527044107692[128] = 0.0;
   out_4618881527044107692[129] = 0.0;
   out_4618881527044107692[130] = 0.0;
   out_4618881527044107692[131] = 0.0;
   out_4618881527044107692[132] = 0.0;
   out_4618881527044107692[133] = 1.0;
   out_4618881527044107692[134] = 0.0;
   out_4618881527044107692[135] = 0.0;
   out_4618881527044107692[136] = 0.0;
   out_4618881527044107692[137] = 0.0;
   out_4618881527044107692[138] = 0.0;
   out_4618881527044107692[139] = 0.0;
   out_4618881527044107692[140] = 0.0;
   out_4618881527044107692[141] = 0.0;
   out_4618881527044107692[142] = 0.0;
   out_4618881527044107692[143] = 0.0;
   out_4618881527044107692[144] = 0.0;
   out_4618881527044107692[145] = 0.0;
   out_4618881527044107692[146] = 0.0;
   out_4618881527044107692[147] = 0.0;
   out_4618881527044107692[148] = 0.0;
   out_4618881527044107692[149] = 0.0;
   out_4618881527044107692[150] = 0.0;
   out_4618881527044107692[151] = 0.0;
   out_4618881527044107692[152] = 1.0;
   out_4618881527044107692[153] = 0.0;
   out_4618881527044107692[154] = 0.0;
   out_4618881527044107692[155] = 0.0;
   out_4618881527044107692[156] = 0.0;
   out_4618881527044107692[157] = 0.0;
   out_4618881527044107692[158] = 0.0;
   out_4618881527044107692[159] = 0.0;
   out_4618881527044107692[160] = 0.0;
   out_4618881527044107692[161] = 0.0;
   out_4618881527044107692[162] = 0.0;
   out_4618881527044107692[163] = 0.0;
   out_4618881527044107692[164] = 0.0;
   out_4618881527044107692[165] = 0.0;
   out_4618881527044107692[166] = 0.0;
   out_4618881527044107692[167] = 0.0;
   out_4618881527044107692[168] = 0.0;
   out_4618881527044107692[169] = 0.0;
   out_4618881527044107692[170] = 0.0;
   out_4618881527044107692[171] = 1.0;
   out_4618881527044107692[172] = 0.0;
   out_4618881527044107692[173] = 0.0;
   out_4618881527044107692[174] = 0.0;
   out_4618881527044107692[175] = 0.0;
   out_4618881527044107692[176] = 0.0;
   out_4618881527044107692[177] = 0.0;
   out_4618881527044107692[178] = 0.0;
   out_4618881527044107692[179] = 0.0;
   out_4618881527044107692[180] = 0.0;
   out_4618881527044107692[181] = 0.0;
   out_4618881527044107692[182] = 0.0;
   out_4618881527044107692[183] = 0.0;
   out_4618881527044107692[184] = 0.0;
   out_4618881527044107692[185] = 0.0;
   out_4618881527044107692[186] = 0.0;
   out_4618881527044107692[187] = 0.0;
   out_4618881527044107692[188] = 0.0;
   out_4618881527044107692[189] = 0.0;
   out_4618881527044107692[190] = 1.0;
   out_4618881527044107692[191] = 0.0;
   out_4618881527044107692[192] = 0.0;
   out_4618881527044107692[193] = 0.0;
   out_4618881527044107692[194] = 0.0;
   out_4618881527044107692[195] = 0.0;
   out_4618881527044107692[196] = 0.0;
   out_4618881527044107692[197] = 0.0;
   out_4618881527044107692[198] = 0.0;
   out_4618881527044107692[199] = 0.0;
   out_4618881527044107692[200] = 0.0;
   out_4618881527044107692[201] = 0.0;
   out_4618881527044107692[202] = 0.0;
   out_4618881527044107692[203] = 0.0;
   out_4618881527044107692[204] = 0.0;
   out_4618881527044107692[205] = 0.0;
   out_4618881527044107692[206] = 0.0;
   out_4618881527044107692[207] = 0.0;
   out_4618881527044107692[208] = 0.0;
   out_4618881527044107692[209] = 1.0;
   out_4618881527044107692[210] = 0.0;
   out_4618881527044107692[211] = 0.0;
   out_4618881527044107692[212] = 0.0;
   out_4618881527044107692[213] = 0.0;
   out_4618881527044107692[214] = 0.0;
   out_4618881527044107692[215] = 0.0;
   out_4618881527044107692[216] = 0.0;
   out_4618881527044107692[217] = 0.0;
   out_4618881527044107692[218] = 0.0;
   out_4618881527044107692[219] = 0.0;
   out_4618881527044107692[220] = 0.0;
   out_4618881527044107692[221] = 0.0;
   out_4618881527044107692[222] = 0.0;
   out_4618881527044107692[223] = 0.0;
   out_4618881527044107692[224] = 0.0;
   out_4618881527044107692[225] = 0.0;
   out_4618881527044107692[226] = 0.0;
   out_4618881527044107692[227] = 0.0;
   out_4618881527044107692[228] = 1.0;
   out_4618881527044107692[229] = 0.0;
   out_4618881527044107692[230] = 0.0;
   out_4618881527044107692[231] = 0.0;
   out_4618881527044107692[232] = 0.0;
   out_4618881527044107692[233] = 0.0;
   out_4618881527044107692[234] = 0.0;
   out_4618881527044107692[235] = 0.0;
   out_4618881527044107692[236] = 0.0;
   out_4618881527044107692[237] = 0.0;
   out_4618881527044107692[238] = 0.0;
   out_4618881527044107692[239] = 0.0;
   out_4618881527044107692[240] = 0.0;
   out_4618881527044107692[241] = 0.0;
   out_4618881527044107692[242] = 0.0;
   out_4618881527044107692[243] = 0.0;
   out_4618881527044107692[244] = 0.0;
   out_4618881527044107692[245] = 0.0;
   out_4618881527044107692[246] = 0.0;
   out_4618881527044107692[247] = 1.0;
   out_4618881527044107692[248] = 0.0;
   out_4618881527044107692[249] = 0.0;
   out_4618881527044107692[250] = 0.0;
   out_4618881527044107692[251] = 0.0;
   out_4618881527044107692[252] = 0.0;
   out_4618881527044107692[253] = 0.0;
   out_4618881527044107692[254] = 0.0;
   out_4618881527044107692[255] = 0.0;
   out_4618881527044107692[256] = 0.0;
   out_4618881527044107692[257] = 0.0;
   out_4618881527044107692[258] = 0.0;
   out_4618881527044107692[259] = 0.0;
   out_4618881527044107692[260] = 0.0;
   out_4618881527044107692[261] = 0.0;
   out_4618881527044107692[262] = 0.0;
   out_4618881527044107692[263] = 0.0;
   out_4618881527044107692[264] = 0.0;
   out_4618881527044107692[265] = 0.0;
   out_4618881527044107692[266] = 1.0;
   out_4618881527044107692[267] = 0.0;
   out_4618881527044107692[268] = 0.0;
   out_4618881527044107692[269] = 0.0;
   out_4618881527044107692[270] = 0.0;
   out_4618881527044107692[271] = 0.0;
   out_4618881527044107692[272] = 0.0;
   out_4618881527044107692[273] = 0.0;
   out_4618881527044107692[274] = 0.0;
   out_4618881527044107692[275] = 0.0;
   out_4618881527044107692[276] = 0.0;
   out_4618881527044107692[277] = 0.0;
   out_4618881527044107692[278] = 0.0;
   out_4618881527044107692[279] = 0.0;
   out_4618881527044107692[280] = 0.0;
   out_4618881527044107692[281] = 0.0;
   out_4618881527044107692[282] = 0.0;
   out_4618881527044107692[283] = 0.0;
   out_4618881527044107692[284] = 0.0;
   out_4618881527044107692[285] = 1.0;
   out_4618881527044107692[286] = 0.0;
   out_4618881527044107692[287] = 0.0;
   out_4618881527044107692[288] = 0.0;
   out_4618881527044107692[289] = 0.0;
   out_4618881527044107692[290] = 0.0;
   out_4618881527044107692[291] = 0.0;
   out_4618881527044107692[292] = 0.0;
   out_4618881527044107692[293] = 0.0;
   out_4618881527044107692[294] = 0.0;
   out_4618881527044107692[295] = 0.0;
   out_4618881527044107692[296] = 0.0;
   out_4618881527044107692[297] = 0.0;
   out_4618881527044107692[298] = 0.0;
   out_4618881527044107692[299] = 0.0;
   out_4618881527044107692[300] = 0.0;
   out_4618881527044107692[301] = 0.0;
   out_4618881527044107692[302] = 0.0;
   out_4618881527044107692[303] = 0.0;
   out_4618881527044107692[304] = 1.0;
   out_4618881527044107692[305] = 0.0;
   out_4618881527044107692[306] = 0.0;
   out_4618881527044107692[307] = 0.0;
   out_4618881527044107692[308] = 0.0;
   out_4618881527044107692[309] = 0.0;
   out_4618881527044107692[310] = 0.0;
   out_4618881527044107692[311] = 0.0;
   out_4618881527044107692[312] = 0.0;
   out_4618881527044107692[313] = 0.0;
   out_4618881527044107692[314] = 0.0;
   out_4618881527044107692[315] = 0.0;
   out_4618881527044107692[316] = 0.0;
   out_4618881527044107692[317] = 0.0;
   out_4618881527044107692[318] = 0.0;
   out_4618881527044107692[319] = 0.0;
   out_4618881527044107692[320] = 0.0;
   out_4618881527044107692[321] = 0.0;
   out_4618881527044107692[322] = 0.0;
   out_4618881527044107692[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_6488051035785602820) {
   out_6488051035785602820[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_6488051035785602820[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_6488051035785602820[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_6488051035785602820[3] = dt*state[12] + state[3];
   out_6488051035785602820[4] = dt*state[13] + state[4];
   out_6488051035785602820[5] = dt*state[14] + state[5];
   out_6488051035785602820[6] = state[6];
   out_6488051035785602820[7] = state[7];
   out_6488051035785602820[8] = state[8];
   out_6488051035785602820[9] = state[9];
   out_6488051035785602820[10] = state[10];
   out_6488051035785602820[11] = state[11];
   out_6488051035785602820[12] = state[12];
   out_6488051035785602820[13] = state[13];
   out_6488051035785602820[14] = state[14];
   out_6488051035785602820[15] = state[15];
   out_6488051035785602820[16] = state[16];
   out_6488051035785602820[17] = state[17];
}
void F_fun(double *state, double dt, double *out_733896468910208221) {
   out_733896468910208221[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_733896468910208221[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_733896468910208221[2] = 0;
   out_733896468910208221[3] = 0;
   out_733896468910208221[4] = 0;
   out_733896468910208221[5] = 0;
   out_733896468910208221[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_733896468910208221[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_733896468910208221[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_733896468910208221[9] = 0;
   out_733896468910208221[10] = 0;
   out_733896468910208221[11] = 0;
   out_733896468910208221[12] = 0;
   out_733896468910208221[13] = 0;
   out_733896468910208221[14] = 0;
   out_733896468910208221[15] = 0;
   out_733896468910208221[16] = 0;
   out_733896468910208221[17] = 0;
   out_733896468910208221[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_733896468910208221[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_733896468910208221[20] = 0;
   out_733896468910208221[21] = 0;
   out_733896468910208221[22] = 0;
   out_733896468910208221[23] = 0;
   out_733896468910208221[24] = 0;
   out_733896468910208221[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_733896468910208221[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_733896468910208221[27] = 0;
   out_733896468910208221[28] = 0;
   out_733896468910208221[29] = 0;
   out_733896468910208221[30] = 0;
   out_733896468910208221[31] = 0;
   out_733896468910208221[32] = 0;
   out_733896468910208221[33] = 0;
   out_733896468910208221[34] = 0;
   out_733896468910208221[35] = 0;
   out_733896468910208221[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_733896468910208221[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_733896468910208221[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_733896468910208221[39] = 0;
   out_733896468910208221[40] = 0;
   out_733896468910208221[41] = 0;
   out_733896468910208221[42] = 0;
   out_733896468910208221[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_733896468910208221[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_733896468910208221[45] = 0;
   out_733896468910208221[46] = 0;
   out_733896468910208221[47] = 0;
   out_733896468910208221[48] = 0;
   out_733896468910208221[49] = 0;
   out_733896468910208221[50] = 0;
   out_733896468910208221[51] = 0;
   out_733896468910208221[52] = 0;
   out_733896468910208221[53] = 0;
   out_733896468910208221[54] = 0;
   out_733896468910208221[55] = 0;
   out_733896468910208221[56] = 0;
   out_733896468910208221[57] = 1;
   out_733896468910208221[58] = 0;
   out_733896468910208221[59] = 0;
   out_733896468910208221[60] = 0;
   out_733896468910208221[61] = 0;
   out_733896468910208221[62] = 0;
   out_733896468910208221[63] = 0;
   out_733896468910208221[64] = 0;
   out_733896468910208221[65] = 0;
   out_733896468910208221[66] = dt;
   out_733896468910208221[67] = 0;
   out_733896468910208221[68] = 0;
   out_733896468910208221[69] = 0;
   out_733896468910208221[70] = 0;
   out_733896468910208221[71] = 0;
   out_733896468910208221[72] = 0;
   out_733896468910208221[73] = 0;
   out_733896468910208221[74] = 0;
   out_733896468910208221[75] = 0;
   out_733896468910208221[76] = 1;
   out_733896468910208221[77] = 0;
   out_733896468910208221[78] = 0;
   out_733896468910208221[79] = 0;
   out_733896468910208221[80] = 0;
   out_733896468910208221[81] = 0;
   out_733896468910208221[82] = 0;
   out_733896468910208221[83] = 0;
   out_733896468910208221[84] = 0;
   out_733896468910208221[85] = dt;
   out_733896468910208221[86] = 0;
   out_733896468910208221[87] = 0;
   out_733896468910208221[88] = 0;
   out_733896468910208221[89] = 0;
   out_733896468910208221[90] = 0;
   out_733896468910208221[91] = 0;
   out_733896468910208221[92] = 0;
   out_733896468910208221[93] = 0;
   out_733896468910208221[94] = 0;
   out_733896468910208221[95] = 1;
   out_733896468910208221[96] = 0;
   out_733896468910208221[97] = 0;
   out_733896468910208221[98] = 0;
   out_733896468910208221[99] = 0;
   out_733896468910208221[100] = 0;
   out_733896468910208221[101] = 0;
   out_733896468910208221[102] = 0;
   out_733896468910208221[103] = 0;
   out_733896468910208221[104] = dt;
   out_733896468910208221[105] = 0;
   out_733896468910208221[106] = 0;
   out_733896468910208221[107] = 0;
   out_733896468910208221[108] = 0;
   out_733896468910208221[109] = 0;
   out_733896468910208221[110] = 0;
   out_733896468910208221[111] = 0;
   out_733896468910208221[112] = 0;
   out_733896468910208221[113] = 0;
   out_733896468910208221[114] = 1;
   out_733896468910208221[115] = 0;
   out_733896468910208221[116] = 0;
   out_733896468910208221[117] = 0;
   out_733896468910208221[118] = 0;
   out_733896468910208221[119] = 0;
   out_733896468910208221[120] = 0;
   out_733896468910208221[121] = 0;
   out_733896468910208221[122] = 0;
   out_733896468910208221[123] = 0;
   out_733896468910208221[124] = 0;
   out_733896468910208221[125] = 0;
   out_733896468910208221[126] = 0;
   out_733896468910208221[127] = 0;
   out_733896468910208221[128] = 0;
   out_733896468910208221[129] = 0;
   out_733896468910208221[130] = 0;
   out_733896468910208221[131] = 0;
   out_733896468910208221[132] = 0;
   out_733896468910208221[133] = 1;
   out_733896468910208221[134] = 0;
   out_733896468910208221[135] = 0;
   out_733896468910208221[136] = 0;
   out_733896468910208221[137] = 0;
   out_733896468910208221[138] = 0;
   out_733896468910208221[139] = 0;
   out_733896468910208221[140] = 0;
   out_733896468910208221[141] = 0;
   out_733896468910208221[142] = 0;
   out_733896468910208221[143] = 0;
   out_733896468910208221[144] = 0;
   out_733896468910208221[145] = 0;
   out_733896468910208221[146] = 0;
   out_733896468910208221[147] = 0;
   out_733896468910208221[148] = 0;
   out_733896468910208221[149] = 0;
   out_733896468910208221[150] = 0;
   out_733896468910208221[151] = 0;
   out_733896468910208221[152] = 1;
   out_733896468910208221[153] = 0;
   out_733896468910208221[154] = 0;
   out_733896468910208221[155] = 0;
   out_733896468910208221[156] = 0;
   out_733896468910208221[157] = 0;
   out_733896468910208221[158] = 0;
   out_733896468910208221[159] = 0;
   out_733896468910208221[160] = 0;
   out_733896468910208221[161] = 0;
   out_733896468910208221[162] = 0;
   out_733896468910208221[163] = 0;
   out_733896468910208221[164] = 0;
   out_733896468910208221[165] = 0;
   out_733896468910208221[166] = 0;
   out_733896468910208221[167] = 0;
   out_733896468910208221[168] = 0;
   out_733896468910208221[169] = 0;
   out_733896468910208221[170] = 0;
   out_733896468910208221[171] = 1;
   out_733896468910208221[172] = 0;
   out_733896468910208221[173] = 0;
   out_733896468910208221[174] = 0;
   out_733896468910208221[175] = 0;
   out_733896468910208221[176] = 0;
   out_733896468910208221[177] = 0;
   out_733896468910208221[178] = 0;
   out_733896468910208221[179] = 0;
   out_733896468910208221[180] = 0;
   out_733896468910208221[181] = 0;
   out_733896468910208221[182] = 0;
   out_733896468910208221[183] = 0;
   out_733896468910208221[184] = 0;
   out_733896468910208221[185] = 0;
   out_733896468910208221[186] = 0;
   out_733896468910208221[187] = 0;
   out_733896468910208221[188] = 0;
   out_733896468910208221[189] = 0;
   out_733896468910208221[190] = 1;
   out_733896468910208221[191] = 0;
   out_733896468910208221[192] = 0;
   out_733896468910208221[193] = 0;
   out_733896468910208221[194] = 0;
   out_733896468910208221[195] = 0;
   out_733896468910208221[196] = 0;
   out_733896468910208221[197] = 0;
   out_733896468910208221[198] = 0;
   out_733896468910208221[199] = 0;
   out_733896468910208221[200] = 0;
   out_733896468910208221[201] = 0;
   out_733896468910208221[202] = 0;
   out_733896468910208221[203] = 0;
   out_733896468910208221[204] = 0;
   out_733896468910208221[205] = 0;
   out_733896468910208221[206] = 0;
   out_733896468910208221[207] = 0;
   out_733896468910208221[208] = 0;
   out_733896468910208221[209] = 1;
   out_733896468910208221[210] = 0;
   out_733896468910208221[211] = 0;
   out_733896468910208221[212] = 0;
   out_733896468910208221[213] = 0;
   out_733896468910208221[214] = 0;
   out_733896468910208221[215] = 0;
   out_733896468910208221[216] = 0;
   out_733896468910208221[217] = 0;
   out_733896468910208221[218] = 0;
   out_733896468910208221[219] = 0;
   out_733896468910208221[220] = 0;
   out_733896468910208221[221] = 0;
   out_733896468910208221[222] = 0;
   out_733896468910208221[223] = 0;
   out_733896468910208221[224] = 0;
   out_733896468910208221[225] = 0;
   out_733896468910208221[226] = 0;
   out_733896468910208221[227] = 0;
   out_733896468910208221[228] = 1;
   out_733896468910208221[229] = 0;
   out_733896468910208221[230] = 0;
   out_733896468910208221[231] = 0;
   out_733896468910208221[232] = 0;
   out_733896468910208221[233] = 0;
   out_733896468910208221[234] = 0;
   out_733896468910208221[235] = 0;
   out_733896468910208221[236] = 0;
   out_733896468910208221[237] = 0;
   out_733896468910208221[238] = 0;
   out_733896468910208221[239] = 0;
   out_733896468910208221[240] = 0;
   out_733896468910208221[241] = 0;
   out_733896468910208221[242] = 0;
   out_733896468910208221[243] = 0;
   out_733896468910208221[244] = 0;
   out_733896468910208221[245] = 0;
   out_733896468910208221[246] = 0;
   out_733896468910208221[247] = 1;
   out_733896468910208221[248] = 0;
   out_733896468910208221[249] = 0;
   out_733896468910208221[250] = 0;
   out_733896468910208221[251] = 0;
   out_733896468910208221[252] = 0;
   out_733896468910208221[253] = 0;
   out_733896468910208221[254] = 0;
   out_733896468910208221[255] = 0;
   out_733896468910208221[256] = 0;
   out_733896468910208221[257] = 0;
   out_733896468910208221[258] = 0;
   out_733896468910208221[259] = 0;
   out_733896468910208221[260] = 0;
   out_733896468910208221[261] = 0;
   out_733896468910208221[262] = 0;
   out_733896468910208221[263] = 0;
   out_733896468910208221[264] = 0;
   out_733896468910208221[265] = 0;
   out_733896468910208221[266] = 1;
   out_733896468910208221[267] = 0;
   out_733896468910208221[268] = 0;
   out_733896468910208221[269] = 0;
   out_733896468910208221[270] = 0;
   out_733896468910208221[271] = 0;
   out_733896468910208221[272] = 0;
   out_733896468910208221[273] = 0;
   out_733896468910208221[274] = 0;
   out_733896468910208221[275] = 0;
   out_733896468910208221[276] = 0;
   out_733896468910208221[277] = 0;
   out_733896468910208221[278] = 0;
   out_733896468910208221[279] = 0;
   out_733896468910208221[280] = 0;
   out_733896468910208221[281] = 0;
   out_733896468910208221[282] = 0;
   out_733896468910208221[283] = 0;
   out_733896468910208221[284] = 0;
   out_733896468910208221[285] = 1;
   out_733896468910208221[286] = 0;
   out_733896468910208221[287] = 0;
   out_733896468910208221[288] = 0;
   out_733896468910208221[289] = 0;
   out_733896468910208221[290] = 0;
   out_733896468910208221[291] = 0;
   out_733896468910208221[292] = 0;
   out_733896468910208221[293] = 0;
   out_733896468910208221[294] = 0;
   out_733896468910208221[295] = 0;
   out_733896468910208221[296] = 0;
   out_733896468910208221[297] = 0;
   out_733896468910208221[298] = 0;
   out_733896468910208221[299] = 0;
   out_733896468910208221[300] = 0;
   out_733896468910208221[301] = 0;
   out_733896468910208221[302] = 0;
   out_733896468910208221[303] = 0;
   out_733896468910208221[304] = 1;
   out_733896468910208221[305] = 0;
   out_733896468910208221[306] = 0;
   out_733896468910208221[307] = 0;
   out_733896468910208221[308] = 0;
   out_733896468910208221[309] = 0;
   out_733896468910208221[310] = 0;
   out_733896468910208221[311] = 0;
   out_733896468910208221[312] = 0;
   out_733896468910208221[313] = 0;
   out_733896468910208221[314] = 0;
   out_733896468910208221[315] = 0;
   out_733896468910208221[316] = 0;
   out_733896468910208221[317] = 0;
   out_733896468910208221[318] = 0;
   out_733896468910208221[319] = 0;
   out_733896468910208221[320] = 0;
   out_733896468910208221[321] = 0;
   out_733896468910208221[322] = 0;
   out_733896468910208221[323] = 1;
}
void h_4(double *state, double *unused, double *out_8117165171672920878) {
   out_8117165171672920878[0] = state[6] + state[9];
   out_8117165171672920878[1] = state[7] + state[10];
   out_8117165171672920878[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_2162528408027234243) {
   out_2162528408027234243[0] = 0;
   out_2162528408027234243[1] = 0;
   out_2162528408027234243[2] = 0;
   out_2162528408027234243[3] = 0;
   out_2162528408027234243[4] = 0;
   out_2162528408027234243[5] = 0;
   out_2162528408027234243[6] = 1;
   out_2162528408027234243[7] = 0;
   out_2162528408027234243[8] = 0;
   out_2162528408027234243[9] = 1;
   out_2162528408027234243[10] = 0;
   out_2162528408027234243[11] = 0;
   out_2162528408027234243[12] = 0;
   out_2162528408027234243[13] = 0;
   out_2162528408027234243[14] = 0;
   out_2162528408027234243[15] = 0;
   out_2162528408027234243[16] = 0;
   out_2162528408027234243[17] = 0;
   out_2162528408027234243[18] = 0;
   out_2162528408027234243[19] = 0;
   out_2162528408027234243[20] = 0;
   out_2162528408027234243[21] = 0;
   out_2162528408027234243[22] = 0;
   out_2162528408027234243[23] = 0;
   out_2162528408027234243[24] = 0;
   out_2162528408027234243[25] = 1;
   out_2162528408027234243[26] = 0;
   out_2162528408027234243[27] = 0;
   out_2162528408027234243[28] = 1;
   out_2162528408027234243[29] = 0;
   out_2162528408027234243[30] = 0;
   out_2162528408027234243[31] = 0;
   out_2162528408027234243[32] = 0;
   out_2162528408027234243[33] = 0;
   out_2162528408027234243[34] = 0;
   out_2162528408027234243[35] = 0;
   out_2162528408027234243[36] = 0;
   out_2162528408027234243[37] = 0;
   out_2162528408027234243[38] = 0;
   out_2162528408027234243[39] = 0;
   out_2162528408027234243[40] = 0;
   out_2162528408027234243[41] = 0;
   out_2162528408027234243[42] = 0;
   out_2162528408027234243[43] = 0;
   out_2162528408027234243[44] = 1;
   out_2162528408027234243[45] = 0;
   out_2162528408027234243[46] = 0;
   out_2162528408027234243[47] = 1;
   out_2162528408027234243[48] = 0;
   out_2162528408027234243[49] = 0;
   out_2162528408027234243[50] = 0;
   out_2162528408027234243[51] = 0;
   out_2162528408027234243[52] = 0;
   out_2162528408027234243[53] = 0;
}
void h_10(double *state, double *unused, double *out_2185975476059121463) {
   out_2185975476059121463[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_2185975476059121463[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_2185975476059121463[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_3758056759224999810) {
   out_3758056759224999810[0] = 0;
   out_3758056759224999810[1] = 9.8100000000000005*cos(state[1]);
   out_3758056759224999810[2] = 0;
   out_3758056759224999810[3] = 0;
   out_3758056759224999810[4] = -state[8];
   out_3758056759224999810[5] = state[7];
   out_3758056759224999810[6] = 0;
   out_3758056759224999810[7] = state[5];
   out_3758056759224999810[8] = -state[4];
   out_3758056759224999810[9] = 0;
   out_3758056759224999810[10] = 0;
   out_3758056759224999810[11] = 0;
   out_3758056759224999810[12] = 1;
   out_3758056759224999810[13] = 0;
   out_3758056759224999810[14] = 0;
   out_3758056759224999810[15] = 1;
   out_3758056759224999810[16] = 0;
   out_3758056759224999810[17] = 0;
   out_3758056759224999810[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_3758056759224999810[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_3758056759224999810[20] = 0;
   out_3758056759224999810[21] = state[8];
   out_3758056759224999810[22] = 0;
   out_3758056759224999810[23] = -state[6];
   out_3758056759224999810[24] = -state[5];
   out_3758056759224999810[25] = 0;
   out_3758056759224999810[26] = state[3];
   out_3758056759224999810[27] = 0;
   out_3758056759224999810[28] = 0;
   out_3758056759224999810[29] = 0;
   out_3758056759224999810[30] = 0;
   out_3758056759224999810[31] = 1;
   out_3758056759224999810[32] = 0;
   out_3758056759224999810[33] = 0;
   out_3758056759224999810[34] = 1;
   out_3758056759224999810[35] = 0;
   out_3758056759224999810[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_3758056759224999810[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_3758056759224999810[38] = 0;
   out_3758056759224999810[39] = -state[7];
   out_3758056759224999810[40] = state[6];
   out_3758056759224999810[41] = 0;
   out_3758056759224999810[42] = state[4];
   out_3758056759224999810[43] = -state[3];
   out_3758056759224999810[44] = 0;
   out_3758056759224999810[45] = 0;
   out_3758056759224999810[46] = 0;
   out_3758056759224999810[47] = 0;
   out_3758056759224999810[48] = 0;
   out_3758056759224999810[49] = 0;
   out_3758056759224999810[50] = 1;
   out_3758056759224999810[51] = 0;
   out_3758056759224999810[52] = 0;
   out_3758056759224999810[53] = 1;
}
void h_13(double *state, double *unused, double *out_5359065950265790886) {
   out_5359065950265790886[0] = state[3];
   out_5359065950265790886[1] = state[4];
   out_5359065950265790886[2] = state[5];
}
void H_13(double *state, double *unused, double *out_1049745417305098558) {
   out_1049745417305098558[0] = 0;
   out_1049745417305098558[1] = 0;
   out_1049745417305098558[2] = 0;
   out_1049745417305098558[3] = 1;
   out_1049745417305098558[4] = 0;
   out_1049745417305098558[5] = 0;
   out_1049745417305098558[6] = 0;
   out_1049745417305098558[7] = 0;
   out_1049745417305098558[8] = 0;
   out_1049745417305098558[9] = 0;
   out_1049745417305098558[10] = 0;
   out_1049745417305098558[11] = 0;
   out_1049745417305098558[12] = 0;
   out_1049745417305098558[13] = 0;
   out_1049745417305098558[14] = 0;
   out_1049745417305098558[15] = 0;
   out_1049745417305098558[16] = 0;
   out_1049745417305098558[17] = 0;
   out_1049745417305098558[18] = 0;
   out_1049745417305098558[19] = 0;
   out_1049745417305098558[20] = 0;
   out_1049745417305098558[21] = 0;
   out_1049745417305098558[22] = 1;
   out_1049745417305098558[23] = 0;
   out_1049745417305098558[24] = 0;
   out_1049745417305098558[25] = 0;
   out_1049745417305098558[26] = 0;
   out_1049745417305098558[27] = 0;
   out_1049745417305098558[28] = 0;
   out_1049745417305098558[29] = 0;
   out_1049745417305098558[30] = 0;
   out_1049745417305098558[31] = 0;
   out_1049745417305098558[32] = 0;
   out_1049745417305098558[33] = 0;
   out_1049745417305098558[34] = 0;
   out_1049745417305098558[35] = 0;
   out_1049745417305098558[36] = 0;
   out_1049745417305098558[37] = 0;
   out_1049745417305098558[38] = 0;
   out_1049745417305098558[39] = 0;
   out_1049745417305098558[40] = 0;
   out_1049745417305098558[41] = 1;
   out_1049745417305098558[42] = 0;
   out_1049745417305098558[43] = 0;
   out_1049745417305098558[44] = 0;
   out_1049745417305098558[45] = 0;
   out_1049745417305098558[46] = 0;
   out_1049745417305098558[47] = 0;
   out_1049745417305098558[48] = 0;
   out_1049745417305098558[49] = 0;
   out_1049745417305098558[50] = 0;
   out_1049745417305098558[51] = 0;
   out_1049745417305098558[52] = 0;
   out_1049745417305098558[53] = 0;
}
void h_14(double *state, double *unused, double *out_2243166911667620430) {
   out_2243166911667620430[0] = state[6];
   out_2243166911667620430[1] = state[7];
   out_2243166911667620430[2] = state[8];
}
void H_14(double *state, double *unused, double *out_1800712448312250286) {
   out_1800712448312250286[0] = 0;
   out_1800712448312250286[1] = 0;
   out_1800712448312250286[2] = 0;
   out_1800712448312250286[3] = 0;
   out_1800712448312250286[4] = 0;
   out_1800712448312250286[5] = 0;
   out_1800712448312250286[6] = 1;
   out_1800712448312250286[7] = 0;
   out_1800712448312250286[8] = 0;
   out_1800712448312250286[9] = 0;
   out_1800712448312250286[10] = 0;
   out_1800712448312250286[11] = 0;
   out_1800712448312250286[12] = 0;
   out_1800712448312250286[13] = 0;
   out_1800712448312250286[14] = 0;
   out_1800712448312250286[15] = 0;
   out_1800712448312250286[16] = 0;
   out_1800712448312250286[17] = 0;
   out_1800712448312250286[18] = 0;
   out_1800712448312250286[19] = 0;
   out_1800712448312250286[20] = 0;
   out_1800712448312250286[21] = 0;
   out_1800712448312250286[22] = 0;
   out_1800712448312250286[23] = 0;
   out_1800712448312250286[24] = 0;
   out_1800712448312250286[25] = 1;
   out_1800712448312250286[26] = 0;
   out_1800712448312250286[27] = 0;
   out_1800712448312250286[28] = 0;
   out_1800712448312250286[29] = 0;
   out_1800712448312250286[30] = 0;
   out_1800712448312250286[31] = 0;
   out_1800712448312250286[32] = 0;
   out_1800712448312250286[33] = 0;
   out_1800712448312250286[34] = 0;
   out_1800712448312250286[35] = 0;
   out_1800712448312250286[36] = 0;
   out_1800712448312250286[37] = 0;
   out_1800712448312250286[38] = 0;
   out_1800712448312250286[39] = 0;
   out_1800712448312250286[40] = 0;
   out_1800712448312250286[41] = 0;
   out_1800712448312250286[42] = 0;
   out_1800712448312250286[43] = 0;
   out_1800712448312250286[44] = 1;
   out_1800712448312250286[45] = 0;
   out_1800712448312250286[46] = 0;
   out_1800712448312250286[47] = 0;
   out_1800712448312250286[48] = 0;
   out_1800712448312250286[49] = 0;
   out_1800712448312250286[50] = 0;
   out_1800712448312250286[51] = 0;
   out_1800712448312250286[52] = 0;
   out_1800712448312250286[53] = 0;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_4, H_4, NULL, in_z, in_R, in_ea, MAHA_THRESH_4);
}
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_10, H_10, NULL, in_z, in_R, in_ea, MAHA_THRESH_10);
}
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_13, H_13, NULL, in_z, in_R, in_ea, MAHA_THRESH_13);
}
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_14, H_14, NULL, in_z, in_R, in_ea, MAHA_THRESH_14);
}
void pose_err_fun(double *nom_x, double *delta_x, double *out_7825504593440143444) {
  err_fun(nom_x, delta_x, out_7825504593440143444);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6707226023055995729) {
  inv_err_fun(nom_x, true_x, out_6707226023055995729);
}
void pose_H_mod_fun(double *state, double *out_4618881527044107692) {
  H_mod_fun(state, out_4618881527044107692);
}
void pose_f_fun(double *state, double dt, double *out_6488051035785602820) {
  f_fun(state,  dt, out_6488051035785602820);
}
void pose_F_fun(double *state, double dt, double *out_733896468910208221) {
  F_fun(state,  dt, out_733896468910208221);
}
void pose_h_4(double *state, double *unused, double *out_8117165171672920878) {
  h_4(state, unused, out_8117165171672920878);
}
void pose_H_4(double *state, double *unused, double *out_2162528408027234243) {
  H_4(state, unused, out_2162528408027234243);
}
void pose_h_10(double *state, double *unused, double *out_2185975476059121463) {
  h_10(state, unused, out_2185975476059121463);
}
void pose_H_10(double *state, double *unused, double *out_3758056759224999810) {
  H_10(state, unused, out_3758056759224999810);
}
void pose_h_13(double *state, double *unused, double *out_5359065950265790886) {
  h_13(state, unused, out_5359065950265790886);
}
void pose_H_13(double *state, double *unused, double *out_1049745417305098558) {
  H_13(state, unused, out_1049745417305098558);
}
void pose_h_14(double *state, double *unused, double *out_2243166911667620430) {
  h_14(state, unused, out_2243166911667620430);
}
void pose_H_14(double *state, double *unused, double *out_1800712448312250286) {
  H_14(state, unused, out_1800712448312250286);
}
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
}

const EKF pose = {
  .name = "pose",
  .kinds = { 4, 10, 13, 14 },
  .feature_kinds = {  },
  .f_fun = pose_f_fun,
  .F_fun = pose_F_fun,
  .err_fun = pose_err_fun,
  .inv_err_fun = pose_inv_err_fun,
  .H_mod_fun = pose_H_mod_fun,
  .predict = pose_predict,
  .hs = {
    { 4, pose_h_4 },
    { 10, pose_h_10 },
    { 13, pose_h_13 },
    { 14, pose_h_14 },
  },
  .Hs = {
    { 4, pose_H_4 },
    { 10, pose_H_10 },
    { 13, pose_H_13 },
    { 14, pose_H_14 },
  },
  .updates = {
    { 4, pose_update_4 },
    { 10, pose_update_10 },
    { 13, pose_update_13 },
    { 14, pose_update_14 },
  },
  .Hes = {
  },
  .sets = {
  },
  .extra_routines = {
  },
};

ekf_lib_init(pose)

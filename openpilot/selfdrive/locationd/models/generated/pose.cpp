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
void err_fun(double *nom_x, double *delta_x, double *out_8909220829729456592) {
   out_8909220829729456592[0] = delta_x[0] + nom_x[0];
   out_8909220829729456592[1] = delta_x[1] + nom_x[1];
   out_8909220829729456592[2] = delta_x[2] + nom_x[2];
   out_8909220829729456592[3] = delta_x[3] + nom_x[3];
   out_8909220829729456592[4] = delta_x[4] + nom_x[4];
   out_8909220829729456592[5] = delta_x[5] + nom_x[5];
   out_8909220829729456592[6] = delta_x[6] + nom_x[6];
   out_8909220829729456592[7] = delta_x[7] + nom_x[7];
   out_8909220829729456592[8] = delta_x[8] + nom_x[8];
   out_8909220829729456592[9] = delta_x[9] + nom_x[9];
   out_8909220829729456592[10] = delta_x[10] + nom_x[10];
   out_8909220829729456592[11] = delta_x[11] + nom_x[11];
   out_8909220829729456592[12] = delta_x[12] + nom_x[12];
   out_8909220829729456592[13] = delta_x[13] + nom_x[13];
   out_8909220829729456592[14] = delta_x[14] + nom_x[14];
   out_8909220829729456592[15] = delta_x[15] + nom_x[15];
   out_8909220829729456592[16] = delta_x[16] + nom_x[16];
   out_8909220829729456592[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_8068156223905085053) {
   out_8068156223905085053[0] = -nom_x[0] + true_x[0];
   out_8068156223905085053[1] = -nom_x[1] + true_x[1];
   out_8068156223905085053[2] = -nom_x[2] + true_x[2];
   out_8068156223905085053[3] = -nom_x[3] + true_x[3];
   out_8068156223905085053[4] = -nom_x[4] + true_x[4];
   out_8068156223905085053[5] = -nom_x[5] + true_x[5];
   out_8068156223905085053[6] = -nom_x[6] + true_x[6];
   out_8068156223905085053[7] = -nom_x[7] + true_x[7];
   out_8068156223905085053[8] = -nom_x[8] + true_x[8];
   out_8068156223905085053[9] = -nom_x[9] + true_x[9];
   out_8068156223905085053[10] = -nom_x[10] + true_x[10];
   out_8068156223905085053[11] = -nom_x[11] + true_x[11];
   out_8068156223905085053[12] = -nom_x[12] + true_x[12];
   out_8068156223905085053[13] = -nom_x[13] + true_x[13];
   out_8068156223905085053[14] = -nom_x[14] + true_x[14];
   out_8068156223905085053[15] = -nom_x[15] + true_x[15];
   out_8068156223905085053[16] = -nom_x[16] + true_x[16];
   out_8068156223905085053[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_3205830260465553476) {
   out_3205830260465553476[0] = 1.0;
   out_3205830260465553476[1] = 0.0;
   out_3205830260465553476[2] = 0.0;
   out_3205830260465553476[3] = 0.0;
   out_3205830260465553476[4] = 0.0;
   out_3205830260465553476[5] = 0.0;
   out_3205830260465553476[6] = 0.0;
   out_3205830260465553476[7] = 0.0;
   out_3205830260465553476[8] = 0.0;
   out_3205830260465553476[9] = 0.0;
   out_3205830260465553476[10] = 0.0;
   out_3205830260465553476[11] = 0.0;
   out_3205830260465553476[12] = 0.0;
   out_3205830260465553476[13] = 0.0;
   out_3205830260465553476[14] = 0.0;
   out_3205830260465553476[15] = 0.0;
   out_3205830260465553476[16] = 0.0;
   out_3205830260465553476[17] = 0.0;
   out_3205830260465553476[18] = 0.0;
   out_3205830260465553476[19] = 1.0;
   out_3205830260465553476[20] = 0.0;
   out_3205830260465553476[21] = 0.0;
   out_3205830260465553476[22] = 0.0;
   out_3205830260465553476[23] = 0.0;
   out_3205830260465553476[24] = 0.0;
   out_3205830260465553476[25] = 0.0;
   out_3205830260465553476[26] = 0.0;
   out_3205830260465553476[27] = 0.0;
   out_3205830260465553476[28] = 0.0;
   out_3205830260465553476[29] = 0.0;
   out_3205830260465553476[30] = 0.0;
   out_3205830260465553476[31] = 0.0;
   out_3205830260465553476[32] = 0.0;
   out_3205830260465553476[33] = 0.0;
   out_3205830260465553476[34] = 0.0;
   out_3205830260465553476[35] = 0.0;
   out_3205830260465553476[36] = 0.0;
   out_3205830260465553476[37] = 0.0;
   out_3205830260465553476[38] = 1.0;
   out_3205830260465553476[39] = 0.0;
   out_3205830260465553476[40] = 0.0;
   out_3205830260465553476[41] = 0.0;
   out_3205830260465553476[42] = 0.0;
   out_3205830260465553476[43] = 0.0;
   out_3205830260465553476[44] = 0.0;
   out_3205830260465553476[45] = 0.0;
   out_3205830260465553476[46] = 0.0;
   out_3205830260465553476[47] = 0.0;
   out_3205830260465553476[48] = 0.0;
   out_3205830260465553476[49] = 0.0;
   out_3205830260465553476[50] = 0.0;
   out_3205830260465553476[51] = 0.0;
   out_3205830260465553476[52] = 0.0;
   out_3205830260465553476[53] = 0.0;
   out_3205830260465553476[54] = 0.0;
   out_3205830260465553476[55] = 0.0;
   out_3205830260465553476[56] = 0.0;
   out_3205830260465553476[57] = 1.0;
   out_3205830260465553476[58] = 0.0;
   out_3205830260465553476[59] = 0.0;
   out_3205830260465553476[60] = 0.0;
   out_3205830260465553476[61] = 0.0;
   out_3205830260465553476[62] = 0.0;
   out_3205830260465553476[63] = 0.0;
   out_3205830260465553476[64] = 0.0;
   out_3205830260465553476[65] = 0.0;
   out_3205830260465553476[66] = 0.0;
   out_3205830260465553476[67] = 0.0;
   out_3205830260465553476[68] = 0.0;
   out_3205830260465553476[69] = 0.0;
   out_3205830260465553476[70] = 0.0;
   out_3205830260465553476[71] = 0.0;
   out_3205830260465553476[72] = 0.0;
   out_3205830260465553476[73] = 0.0;
   out_3205830260465553476[74] = 0.0;
   out_3205830260465553476[75] = 0.0;
   out_3205830260465553476[76] = 1.0;
   out_3205830260465553476[77] = 0.0;
   out_3205830260465553476[78] = 0.0;
   out_3205830260465553476[79] = 0.0;
   out_3205830260465553476[80] = 0.0;
   out_3205830260465553476[81] = 0.0;
   out_3205830260465553476[82] = 0.0;
   out_3205830260465553476[83] = 0.0;
   out_3205830260465553476[84] = 0.0;
   out_3205830260465553476[85] = 0.0;
   out_3205830260465553476[86] = 0.0;
   out_3205830260465553476[87] = 0.0;
   out_3205830260465553476[88] = 0.0;
   out_3205830260465553476[89] = 0.0;
   out_3205830260465553476[90] = 0.0;
   out_3205830260465553476[91] = 0.0;
   out_3205830260465553476[92] = 0.0;
   out_3205830260465553476[93] = 0.0;
   out_3205830260465553476[94] = 0.0;
   out_3205830260465553476[95] = 1.0;
   out_3205830260465553476[96] = 0.0;
   out_3205830260465553476[97] = 0.0;
   out_3205830260465553476[98] = 0.0;
   out_3205830260465553476[99] = 0.0;
   out_3205830260465553476[100] = 0.0;
   out_3205830260465553476[101] = 0.0;
   out_3205830260465553476[102] = 0.0;
   out_3205830260465553476[103] = 0.0;
   out_3205830260465553476[104] = 0.0;
   out_3205830260465553476[105] = 0.0;
   out_3205830260465553476[106] = 0.0;
   out_3205830260465553476[107] = 0.0;
   out_3205830260465553476[108] = 0.0;
   out_3205830260465553476[109] = 0.0;
   out_3205830260465553476[110] = 0.0;
   out_3205830260465553476[111] = 0.0;
   out_3205830260465553476[112] = 0.0;
   out_3205830260465553476[113] = 0.0;
   out_3205830260465553476[114] = 1.0;
   out_3205830260465553476[115] = 0.0;
   out_3205830260465553476[116] = 0.0;
   out_3205830260465553476[117] = 0.0;
   out_3205830260465553476[118] = 0.0;
   out_3205830260465553476[119] = 0.0;
   out_3205830260465553476[120] = 0.0;
   out_3205830260465553476[121] = 0.0;
   out_3205830260465553476[122] = 0.0;
   out_3205830260465553476[123] = 0.0;
   out_3205830260465553476[124] = 0.0;
   out_3205830260465553476[125] = 0.0;
   out_3205830260465553476[126] = 0.0;
   out_3205830260465553476[127] = 0.0;
   out_3205830260465553476[128] = 0.0;
   out_3205830260465553476[129] = 0.0;
   out_3205830260465553476[130] = 0.0;
   out_3205830260465553476[131] = 0.0;
   out_3205830260465553476[132] = 0.0;
   out_3205830260465553476[133] = 1.0;
   out_3205830260465553476[134] = 0.0;
   out_3205830260465553476[135] = 0.0;
   out_3205830260465553476[136] = 0.0;
   out_3205830260465553476[137] = 0.0;
   out_3205830260465553476[138] = 0.0;
   out_3205830260465553476[139] = 0.0;
   out_3205830260465553476[140] = 0.0;
   out_3205830260465553476[141] = 0.0;
   out_3205830260465553476[142] = 0.0;
   out_3205830260465553476[143] = 0.0;
   out_3205830260465553476[144] = 0.0;
   out_3205830260465553476[145] = 0.0;
   out_3205830260465553476[146] = 0.0;
   out_3205830260465553476[147] = 0.0;
   out_3205830260465553476[148] = 0.0;
   out_3205830260465553476[149] = 0.0;
   out_3205830260465553476[150] = 0.0;
   out_3205830260465553476[151] = 0.0;
   out_3205830260465553476[152] = 1.0;
   out_3205830260465553476[153] = 0.0;
   out_3205830260465553476[154] = 0.0;
   out_3205830260465553476[155] = 0.0;
   out_3205830260465553476[156] = 0.0;
   out_3205830260465553476[157] = 0.0;
   out_3205830260465553476[158] = 0.0;
   out_3205830260465553476[159] = 0.0;
   out_3205830260465553476[160] = 0.0;
   out_3205830260465553476[161] = 0.0;
   out_3205830260465553476[162] = 0.0;
   out_3205830260465553476[163] = 0.0;
   out_3205830260465553476[164] = 0.0;
   out_3205830260465553476[165] = 0.0;
   out_3205830260465553476[166] = 0.0;
   out_3205830260465553476[167] = 0.0;
   out_3205830260465553476[168] = 0.0;
   out_3205830260465553476[169] = 0.0;
   out_3205830260465553476[170] = 0.0;
   out_3205830260465553476[171] = 1.0;
   out_3205830260465553476[172] = 0.0;
   out_3205830260465553476[173] = 0.0;
   out_3205830260465553476[174] = 0.0;
   out_3205830260465553476[175] = 0.0;
   out_3205830260465553476[176] = 0.0;
   out_3205830260465553476[177] = 0.0;
   out_3205830260465553476[178] = 0.0;
   out_3205830260465553476[179] = 0.0;
   out_3205830260465553476[180] = 0.0;
   out_3205830260465553476[181] = 0.0;
   out_3205830260465553476[182] = 0.0;
   out_3205830260465553476[183] = 0.0;
   out_3205830260465553476[184] = 0.0;
   out_3205830260465553476[185] = 0.0;
   out_3205830260465553476[186] = 0.0;
   out_3205830260465553476[187] = 0.0;
   out_3205830260465553476[188] = 0.0;
   out_3205830260465553476[189] = 0.0;
   out_3205830260465553476[190] = 1.0;
   out_3205830260465553476[191] = 0.0;
   out_3205830260465553476[192] = 0.0;
   out_3205830260465553476[193] = 0.0;
   out_3205830260465553476[194] = 0.0;
   out_3205830260465553476[195] = 0.0;
   out_3205830260465553476[196] = 0.0;
   out_3205830260465553476[197] = 0.0;
   out_3205830260465553476[198] = 0.0;
   out_3205830260465553476[199] = 0.0;
   out_3205830260465553476[200] = 0.0;
   out_3205830260465553476[201] = 0.0;
   out_3205830260465553476[202] = 0.0;
   out_3205830260465553476[203] = 0.0;
   out_3205830260465553476[204] = 0.0;
   out_3205830260465553476[205] = 0.0;
   out_3205830260465553476[206] = 0.0;
   out_3205830260465553476[207] = 0.0;
   out_3205830260465553476[208] = 0.0;
   out_3205830260465553476[209] = 1.0;
   out_3205830260465553476[210] = 0.0;
   out_3205830260465553476[211] = 0.0;
   out_3205830260465553476[212] = 0.0;
   out_3205830260465553476[213] = 0.0;
   out_3205830260465553476[214] = 0.0;
   out_3205830260465553476[215] = 0.0;
   out_3205830260465553476[216] = 0.0;
   out_3205830260465553476[217] = 0.0;
   out_3205830260465553476[218] = 0.0;
   out_3205830260465553476[219] = 0.0;
   out_3205830260465553476[220] = 0.0;
   out_3205830260465553476[221] = 0.0;
   out_3205830260465553476[222] = 0.0;
   out_3205830260465553476[223] = 0.0;
   out_3205830260465553476[224] = 0.0;
   out_3205830260465553476[225] = 0.0;
   out_3205830260465553476[226] = 0.0;
   out_3205830260465553476[227] = 0.0;
   out_3205830260465553476[228] = 1.0;
   out_3205830260465553476[229] = 0.0;
   out_3205830260465553476[230] = 0.0;
   out_3205830260465553476[231] = 0.0;
   out_3205830260465553476[232] = 0.0;
   out_3205830260465553476[233] = 0.0;
   out_3205830260465553476[234] = 0.0;
   out_3205830260465553476[235] = 0.0;
   out_3205830260465553476[236] = 0.0;
   out_3205830260465553476[237] = 0.0;
   out_3205830260465553476[238] = 0.0;
   out_3205830260465553476[239] = 0.0;
   out_3205830260465553476[240] = 0.0;
   out_3205830260465553476[241] = 0.0;
   out_3205830260465553476[242] = 0.0;
   out_3205830260465553476[243] = 0.0;
   out_3205830260465553476[244] = 0.0;
   out_3205830260465553476[245] = 0.0;
   out_3205830260465553476[246] = 0.0;
   out_3205830260465553476[247] = 1.0;
   out_3205830260465553476[248] = 0.0;
   out_3205830260465553476[249] = 0.0;
   out_3205830260465553476[250] = 0.0;
   out_3205830260465553476[251] = 0.0;
   out_3205830260465553476[252] = 0.0;
   out_3205830260465553476[253] = 0.0;
   out_3205830260465553476[254] = 0.0;
   out_3205830260465553476[255] = 0.0;
   out_3205830260465553476[256] = 0.0;
   out_3205830260465553476[257] = 0.0;
   out_3205830260465553476[258] = 0.0;
   out_3205830260465553476[259] = 0.0;
   out_3205830260465553476[260] = 0.0;
   out_3205830260465553476[261] = 0.0;
   out_3205830260465553476[262] = 0.0;
   out_3205830260465553476[263] = 0.0;
   out_3205830260465553476[264] = 0.0;
   out_3205830260465553476[265] = 0.0;
   out_3205830260465553476[266] = 1.0;
   out_3205830260465553476[267] = 0.0;
   out_3205830260465553476[268] = 0.0;
   out_3205830260465553476[269] = 0.0;
   out_3205830260465553476[270] = 0.0;
   out_3205830260465553476[271] = 0.0;
   out_3205830260465553476[272] = 0.0;
   out_3205830260465553476[273] = 0.0;
   out_3205830260465553476[274] = 0.0;
   out_3205830260465553476[275] = 0.0;
   out_3205830260465553476[276] = 0.0;
   out_3205830260465553476[277] = 0.0;
   out_3205830260465553476[278] = 0.0;
   out_3205830260465553476[279] = 0.0;
   out_3205830260465553476[280] = 0.0;
   out_3205830260465553476[281] = 0.0;
   out_3205830260465553476[282] = 0.0;
   out_3205830260465553476[283] = 0.0;
   out_3205830260465553476[284] = 0.0;
   out_3205830260465553476[285] = 1.0;
   out_3205830260465553476[286] = 0.0;
   out_3205830260465553476[287] = 0.0;
   out_3205830260465553476[288] = 0.0;
   out_3205830260465553476[289] = 0.0;
   out_3205830260465553476[290] = 0.0;
   out_3205830260465553476[291] = 0.0;
   out_3205830260465553476[292] = 0.0;
   out_3205830260465553476[293] = 0.0;
   out_3205830260465553476[294] = 0.0;
   out_3205830260465553476[295] = 0.0;
   out_3205830260465553476[296] = 0.0;
   out_3205830260465553476[297] = 0.0;
   out_3205830260465553476[298] = 0.0;
   out_3205830260465553476[299] = 0.0;
   out_3205830260465553476[300] = 0.0;
   out_3205830260465553476[301] = 0.0;
   out_3205830260465553476[302] = 0.0;
   out_3205830260465553476[303] = 0.0;
   out_3205830260465553476[304] = 1.0;
   out_3205830260465553476[305] = 0.0;
   out_3205830260465553476[306] = 0.0;
   out_3205830260465553476[307] = 0.0;
   out_3205830260465553476[308] = 0.0;
   out_3205830260465553476[309] = 0.0;
   out_3205830260465553476[310] = 0.0;
   out_3205830260465553476[311] = 0.0;
   out_3205830260465553476[312] = 0.0;
   out_3205830260465553476[313] = 0.0;
   out_3205830260465553476[314] = 0.0;
   out_3205830260465553476[315] = 0.0;
   out_3205830260465553476[316] = 0.0;
   out_3205830260465553476[317] = 0.0;
   out_3205830260465553476[318] = 0.0;
   out_3205830260465553476[319] = 0.0;
   out_3205830260465553476[320] = 0.0;
   out_3205830260465553476[321] = 0.0;
   out_3205830260465553476[322] = 0.0;
   out_3205830260465553476[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_4238396293587501899) {
   out_4238396293587501899[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_4238396293587501899[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_4238396293587501899[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_4238396293587501899[3] = dt*state[12] + state[3];
   out_4238396293587501899[4] = dt*state[13] + state[4];
   out_4238396293587501899[5] = dt*state[14] + state[5];
   out_4238396293587501899[6] = state[6];
   out_4238396293587501899[7] = state[7];
   out_4238396293587501899[8] = state[8];
   out_4238396293587501899[9] = state[9];
   out_4238396293587501899[10] = state[10];
   out_4238396293587501899[11] = state[11];
   out_4238396293587501899[12] = state[12];
   out_4238396293587501899[13] = state[13];
   out_4238396293587501899[14] = state[14];
   out_4238396293587501899[15] = state[15];
   out_4238396293587501899[16] = state[16];
   out_4238396293587501899[17] = state[17];
}
void F_fun(double *state, double dt, double *out_6003141237729326165) {
   out_6003141237729326165[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6003141237729326165[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6003141237729326165[2] = 0;
   out_6003141237729326165[3] = 0;
   out_6003141237729326165[4] = 0;
   out_6003141237729326165[5] = 0;
   out_6003141237729326165[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6003141237729326165[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6003141237729326165[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6003141237729326165[9] = 0;
   out_6003141237729326165[10] = 0;
   out_6003141237729326165[11] = 0;
   out_6003141237729326165[12] = 0;
   out_6003141237729326165[13] = 0;
   out_6003141237729326165[14] = 0;
   out_6003141237729326165[15] = 0;
   out_6003141237729326165[16] = 0;
   out_6003141237729326165[17] = 0;
   out_6003141237729326165[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6003141237729326165[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6003141237729326165[20] = 0;
   out_6003141237729326165[21] = 0;
   out_6003141237729326165[22] = 0;
   out_6003141237729326165[23] = 0;
   out_6003141237729326165[24] = 0;
   out_6003141237729326165[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6003141237729326165[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6003141237729326165[27] = 0;
   out_6003141237729326165[28] = 0;
   out_6003141237729326165[29] = 0;
   out_6003141237729326165[30] = 0;
   out_6003141237729326165[31] = 0;
   out_6003141237729326165[32] = 0;
   out_6003141237729326165[33] = 0;
   out_6003141237729326165[34] = 0;
   out_6003141237729326165[35] = 0;
   out_6003141237729326165[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6003141237729326165[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6003141237729326165[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6003141237729326165[39] = 0;
   out_6003141237729326165[40] = 0;
   out_6003141237729326165[41] = 0;
   out_6003141237729326165[42] = 0;
   out_6003141237729326165[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6003141237729326165[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6003141237729326165[45] = 0;
   out_6003141237729326165[46] = 0;
   out_6003141237729326165[47] = 0;
   out_6003141237729326165[48] = 0;
   out_6003141237729326165[49] = 0;
   out_6003141237729326165[50] = 0;
   out_6003141237729326165[51] = 0;
   out_6003141237729326165[52] = 0;
   out_6003141237729326165[53] = 0;
   out_6003141237729326165[54] = 0;
   out_6003141237729326165[55] = 0;
   out_6003141237729326165[56] = 0;
   out_6003141237729326165[57] = 1;
   out_6003141237729326165[58] = 0;
   out_6003141237729326165[59] = 0;
   out_6003141237729326165[60] = 0;
   out_6003141237729326165[61] = 0;
   out_6003141237729326165[62] = 0;
   out_6003141237729326165[63] = 0;
   out_6003141237729326165[64] = 0;
   out_6003141237729326165[65] = 0;
   out_6003141237729326165[66] = dt;
   out_6003141237729326165[67] = 0;
   out_6003141237729326165[68] = 0;
   out_6003141237729326165[69] = 0;
   out_6003141237729326165[70] = 0;
   out_6003141237729326165[71] = 0;
   out_6003141237729326165[72] = 0;
   out_6003141237729326165[73] = 0;
   out_6003141237729326165[74] = 0;
   out_6003141237729326165[75] = 0;
   out_6003141237729326165[76] = 1;
   out_6003141237729326165[77] = 0;
   out_6003141237729326165[78] = 0;
   out_6003141237729326165[79] = 0;
   out_6003141237729326165[80] = 0;
   out_6003141237729326165[81] = 0;
   out_6003141237729326165[82] = 0;
   out_6003141237729326165[83] = 0;
   out_6003141237729326165[84] = 0;
   out_6003141237729326165[85] = dt;
   out_6003141237729326165[86] = 0;
   out_6003141237729326165[87] = 0;
   out_6003141237729326165[88] = 0;
   out_6003141237729326165[89] = 0;
   out_6003141237729326165[90] = 0;
   out_6003141237729326165[91] = 0;
   out_6003141237729326165[92] = 0;
   out_6003141237729326165[93] = 0;
   out_6003141237729326165[94] = 0;
   out_6003141237729326165[95] = 1;
   out_6003141237729326165[96] = 0;
   out_6003141237729326165[97] = 0;
   out_6003141237729326165[98] = 0;
   out_6003141237729326165[99] = 0;
   out_6003141237729326165[100] = 0;
   out_6003141237729326165[101] = 0;
   out_6003141237729326165[102] = 0;
   out_6003141237729326165[103] = 0;
   out_6003141237729326165[104] = dt;
   out_6003141237729326165[105] = 0;
   out_6003141237729326165[106] = 0;
   out_6003141237729326165[107] = 0;
   out_6003141237729326165[108] = 0;
   out_6003141237729326165[109] = 0;
   out_6003141237729326165[110] = 0;
   out_6003141237729326165[111] = 0;
   out_6003141237729326165[112] = 0;
   out_6003141237729326165[113] = 0;
   out_6003141237729326165[114] = 1;
   out_6003141237729326165[115] = 0;
   out_6003141237729326165[116] = 0;
   out_6003141237729326165[117] = 0;
   out_6003141237729326165[118] = 0;
   out_6003141237729326165[119] = 0;
   out_6003141237729326165[120] = 0;
   out_6003141237729326165[121] = 0;
   out_6003141237729326165[122] = 0;
   out_6003141237729326165[123] = 0;
   out_6003141237729326165[124] = 0;
   out_6003141237729326165[125] = 0;
   out_6003141237729326165[126] = 0;
   out_6003141237729326165[127] = 0;
   out_6003141237729326165[128] = 0;
   out_6003141237729326165[129] = 0;
   out_6003141237729326165[130] = 0;
   out_6003141237729326165[131] = 0;
   out_6003141237729326165[132] = 0;
   out_6003141237729326165[133] = 1;
   out_6003141237729326165[134] = 0;
   out_6003141237729326165[135] = 0;
   out_6003141237729326165[136] = 0;
   out_6003141237729326165[137] = 0;
   out_6003141237729326165[138] = 0;
   out_6003141237729326165[139] = 0;
   out_6003141237729326165[140] = 0;
   out_6003141237729326165[141] = 0;
   out_6003141237729326165[142] = 0;
   out_6003141237729326165[143] = 0;
   out_6003141237729326165[144] = 0;
   out_6003141237729326165[145] = 0;
   out_6003141237729326165[146] = 0;
   out_6003141237729326165[147] = 0;
   out_6003141237729326165[148] = 0;
   out_6003141237729326165[149] = 0;
   out_6003141237729326165[150] = 0;
   out_6003141237729326165[151] = 0;
   out_6003141237729326165[152] = 1;
   out_6003141237729326165[153] = 0;
   out_6003141237729326165[154] = 0;
   out_6003141237729326165[155] = 0;
   out_6003141237729326165[156] = 0;
   out_6003141237729326165[157] = 0;
   out_6003141237729326165[158] = 0;
   out_6003141237729326165[159] = 0;
   out_6003141237729326165[160] = 0;
   out_6003141237729326165[161] = 0;
   out_6003141237729326165[162] = 0;
   out_6003141237729326165[163] = 0;
   out_6003141237729326165[164] = 0;
   out_6003141237729326165[165] = 0;
   out_6003141237729326165[166] = 0;
   out_6003141237729326165[167] = 0;
   out_6003141237729326165[168] = 0;
   out_6003141237729326165[169] = 0;
   out_6003141237729326165[170] = 0;
   out_6003141237729326165[171] = 1;
   out_6003141237729326165[172] = 0;
   out_6003141237729326165[173] = 0;
   out_6003141237729326165[174] = 0;
   out_6003141237729326165[175] = 0;
   out_6003141237729326165[176] = 0;
   out_6003141237729326165[177] = 0;
   out_6003141237729326165[178] = 0;
   out_6003141237729326165[179] = 0;
   out_6003141237729326165[180] = 0;
   out_6003141237729326165[181] = 0;
   out_6003141237729326165[182] = 0;
   out_6003141237729326165[183] = 0;
   out_6003141237729326165[184] = 0;
   out_6003141237729326165[185] = 0;
   out_6003141237729326165[186] = 0;
   out_6003141237729326165[187] = 0;
   out_6003141237729326165[188] = 0;
   out_6003141237729326165[189] = 0;
   out_6003141237729326165[190] = 1;
   out_6003141237729326165[191] = 0;
   out_6003141237729326165[192] = 0;
   out_6003141237729326165[193] = 0;
   out_6003141237729326165[194] = 0;
   out_6003141237729326165[195] = 0;
   out_6003141237729326165[196] = 0;
   out_6003141237729326165[197] = 0;
   out_6003141237729326165[198] = 0;
   out_6003141237729326165[199] = 0;
   out_6003141237729326165[200] = 0;
   out_6003141237729326165[201] = 0;
   out_6003141237729326165[202] = 0;
   out_6003141237729326165[203] = 0;
   out_6003141237729326165[204] = 0;
   out_6003141237729326165[205] = 0;
   out_6003141237729326165[206] = 0;
   out_6003141237729326165[207] = 0;
   out_6003141237729326165[208] = 0;
   out_6003141237729326165[209] = 1;
   out_6003141237729326165[210] = 0;
   out_6003141237729326165[211] = 0;
   out_6003141237729326165[212] = 0;
   out_6003141237729326165[213] = 0;
   out_6003141237729326165[214] = 0;
   out_6003141237729326165[215] = 0;
   out_6003141237729326165[216] = 0;
   out_6003141237729326165[217] = 0;
   out_6003141237729326165[218] = 0;
   out_6003141237729326165[219] = 0;
   out_6003141237729326165[220] = 0;
   out_6003141237729326165[221] = 0;
   out_6003141237729326165[222] = 0;
   out_6003141237729326165[223] = 0;
   out_6003141237729326165[224] = 0;
   out_6003141237729326165[225] = 0;
   out_6003141237729326165[226] = 0;
   out_6003141237729326165[227] = 0;
   out_6003141237729326165[228] = 1;
   out_6003141237729326165[229] = 0;
   out_6003141237729326165[230] = 0;
   out_6003141237729326165[231] = 0;
   out_6003141237729326165[232] = 0;
   out_6003141237729326165[233] = 0;
   out_6003141237729326165[234] = 0;
   out_6003141237729326165[235] = 0;
   out_6003141237729326165[236] = 0;
   out_6003141237729326165[237] = 0;
   out_6003141237729326165[238] = 0;
   out_6003141237729326165[239] = 0;
   out_6003141237729326165[240] = 0;
   out_6003141237729326165[241] = 0;
   out_6003141237729326165[242] = 0;
   out_6003141237729326165[243] = 0;
   out_6003141237729326165[244] = 0;
   out_6003141237729326165[245] = 0;
   out_6003141237729326165[246] = 0;
   out_6003141237729326165[247] = 1;
   out_6003141237729326165[248] = 0;
   out_6003141237729326165[249] = 0;
   out_6003141237729326165[250] = 0;
   out_6003141237729326165[251] = 0;
   out_6003141237729326165[252] = 0;
   out_6003141237729326165[253] = 0;
   out_6003141237729326165[254] = 0;
   out_6003141237729326165[255] = 0;
   out_6003141237729326165[256] = 0;
   out_6003141237729326165[257] = 0;
   out_6003141237729326165[258] = 0;
   out_6003141237729326165[259] = 0;
   out_6003141237729326165[260] = 0;
   out_6003141237729326165[261] = 0;
   out_6003141237729326165[262] = 0;
   out_6003141237729326165[263] = 0;
   out_6003141237729326165[264] = 0;
   out_6003141237729326165[265] = 0;
   out_6003141237729326165[266] = 1;
   out_6003141237729326165[267] = 0;
   out_6003141237729326165[268] = 0;
   out_6003141237729326165[269] = 0;
   out_6003141237729326165[270] = 0;
   out_6003141237729326165[271] = 0;
   out_6003141237729326165[272] = 0;
   out_6003141237729326165[273] = 0;
   out_6003141237729326165[274] = 0;
   out_6003141237729326165[275] = 0;
   out_6003141237729326165[276] = 0;
   out_6003141237729326165[277] = 0;
   out_6003141237729326165[278] = 0;
   out_6003141237729326165[279] = 0;
   out_6003141237729326165[280] = 0;
   out_6003141237729326165[281] = 0;
   out_6003141237729326165[282] = 0;
   out_6003141237729326165[283] = 0;
   out_6003141237729326165[284] = 0;
   out_6003141237729326165[285] = 1;
   out_6003141237729326165[286] = 0;
   out_6003141237729326165[287] = 0;
   out_6003141237729326165[288] = 0;
   out_6003141237729326165[289] = 0;
   out_6003141237729326165[290] = 0;
   out_6003141237729326165[291] = 0;
   out_6003141237729326165[292] = 0;
   out_6003141237729326165[293] = 0;
   out_6003141237729326165[294] = 0;
   out_6003141237729326165[295] = 0;
   out_6003141237729326165[296] = 0;
   out_6003141237729326165[297] = 0;
   out_6003141237729326165[298] = 0;
   out_6003141237729326165[299] = 0;
   out_6003141237729326165[300] = 0;
   out_6003141237729326165[301] = 0;
   out_6003141237729326165[302] = 0;
   out_6003141237729326165[303] = 0;
   out_6003141237729326165[304] = 1;
   out_6003141237729326165[305] = 0;
   out_6003141237729326165[306] = 0;
   out_6003141237729326165[307] = 0;
   out_6003141237729326165[308] = 0;
   out_6003141237729326165[309] = 0;
   out_6003141237729326165[310] = 0;
   out_6003141237729326165[311] = 0;
   out_6003141237729326165[312] = 0;
   out_6003141237729326165[313] = 0;
   out_6003141237729326165[314] = 0;
   out_6003141237729326165[315] = 0;
   out_6003141237729326165[316] = 0;
   out_6003141237729326165[317] = 0;
   out_6003141237729326165[318] = 0;
   out_6003141237729326165[319] = 0;
   out_6003141237729326165[320] = 0;
   out_6003141237729326165[321] = 0;
   out_6003141237729326165[322] = 0;
   out_6003141237729326165[323] = 1;
}
void h_4(double *state, double *unused, double *out_6516003908446642780) {
   out_6516003908446642780[0] = state[6] + state[9];
   out_6516003908446642780[1] = state[7] + state[10];
   out_6516003908446642780[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_8358348645504634211) {
   out_8358348645504634211[0] = 0;
   out_8358348645504634211[1] = 0;
   out_8358348645504634211[2] = 0;
   out_8358348645504634211[3] = 0;
   out_8358348645504634211[4] = 0;
   out_8358348645504634211[5] = 0;
   out_8358348645504634211[6] = 1;
   out_8358348645504634211[7] = 0;
   out_8358348645504634211[8] = 0;
   out_8358348645504634211[9] = 1;
   out_8358348645504634211[10] = 0;
   out_8358348645504634211[11] = 0;
   out_8358348645504634211[12] = 0;
   out_8358348645504634211[13] = 0;
   out_8358348645504634211[14] = 0;
   out_8358348645504634211[15] = 0;
   out_8358348645504634211[16] = 0;
   out_8358348645504634211[17] = 0;
   out_8358348645504634211[18] = 0;
   out_8358348645504634211[19] = 0;
   out_8358348645504634211[20] = 0;
   out_8358348645504634211[21] = 0;
   out_8358348645504634211[22] = 0;
   out_8358348645504634211[23] = 0;
   out_8358348645504634211[24] = 0;
   out_8358348645504634211[25] = 1;
   out_8358348645504634211[26] = 0;
   out_8358348645504634211[27] = 0;
   out_8358348645504634211[28] = 1;
   out_8358348645504634211[29] = 0;
   out_8358348645504634211[30] = 0;
   out_8358348645504634211[31] = 0;
   out_8358348645504634211[32] = 0;
   out_8358348645504634211[33] = 0;
   out_8358348645504634211[34] = 0;
   out_8358348645504634211[35] = 0;
   out_8358348645504634211[36] = 0;
   out_8358348645504634211[37] = 0;
   out_8358348645504634211[38] = 0;
   out_8358348645504634211[39] = 0;
   out_8358348645504634211[40] = 0;
   out_8358348645504634211[41] = 0;
   out_8358348645504634211[42] = 0;
   out_8358348645504634211[43] = 0;
   out_8358348645504634211[44] = 1;
   out_8358348645504634211[45] = 0;
   out_8358348645504634211[46] = 0;
   out_8358348645504634211[47] = 1;
   out_8358348645504634211[48] = 0;
   out_8358348645504634211[49] = 0;
   out_8358348645504634211[50] = 0;
   out_8358348645504634211[51] = 0;
   out_8358348645504634211[52] = 0;
   out_8358348645504634211[53] = 0;
}
void h_10(double *state, double *unused, double *out_5069419514865957544) {
   out_5069419514865957544[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_5069419514865957544[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_5069419514865957544[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_2285557584559061390) {
   out_2285557584559061390[0] = 0;
   out_2285557584559061390[1] = 9.8100000000000005*cos(state[1]);
   out_2285557584559061390[2] = 0;
   out_2285557584559061390[3] = 0;
   out_2285557584559061390[4] = -state[8];
   out_2285557584559061390[5] = state[7];
   out_2285557584559061390[6] = 0;
   out_2285557584559061390[7] = state[5];
   out_2285557584559061390[8] = -state[4];
   out_2285557584559061390[9] = 0;
   out_2285557584559061390[10] = 0;
   out_2285557584559061390[11] = 0;
   out_2285557584559061390[12] = 1;
   out_2285557584559061390[13] = 0;
   out_2285557584559061390[14] = 0;
   out_2285557584559061390[15] = 1;
   out_2285557584559061390[16] = 0;
   out_2285557584559061390[17] = 0;
   out_2285557584559061390[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_2285557584559061390[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_2285557584559061390[20] = 0;
   out_2285557584559061390[21] = state[8];
   out_2285557584559061390[22] = 0;
   out_2285557584559061390[23] = -state[6];
   out_2285557584559061390[24] = -state[5];
   out_2285557584559061390[25] = 0;
   out_2285557584559061390[26] = state[3];
   out_2285557584559061390[27] = 0;
   out_2285557584559061390[28] = 0;
   out_2285557584559061390[29] = 0;
   out_2285557584559061390[30] = 0;
   out_2285557584559061390[31] = 1;
   out_2285557584559061390[32] = 0;
   out_2285557584559061390[33] = 0;
   out_2285557584559061390[34] = 1;
   out_2285557584559061390[35] = 0;
   out_2285557584559061390[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_2285557584559061390[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_2285557584559061390[38] = 0;
   out_2285557584559061390[39] = -state[7];
   out_2285557584559061390[40] = state[6];
   out_2285557584559061390[41] = 0;
   out_2285557584559061390[42] = state[4];
   out_2285557584559061390[43] = -state[3];
   out_2285557584559061390[44] = 0;
   out_2285557584559061390[45] = 0;
   out_2285557584559061390[46] = 0;
   out_2285557584559061390[47] = 0;
   out_2285557584559061390[48] = 0;
   out_2285557584559061390[49] = 0;
   out_2285557584559061390[50] = 1;
   out_2285557584559061390[51] = 0;
   out_2285557584559061390[52] = 0;
   out_2285557584559061390[53] = 1;
}
void h_13(double *state, double *unused, double *out_3114619426317878324) {
   out_3114619426317878324[0] = state[3];
   out_3114619426317878324[1] = state[4];
   out_3114619426317878324[2] = state[5];
}
void H_13(double *state, double *unused, double *out_6876121602872584604) {
   out_6876121602872584604[0] = 0;
   out_6876121602872584604[1] = 0;
   out_6876121602872584604[2] = 0;
   out_6876121602872584604[3] = 1;
   out_6876121602872584604[4] = 0;
   out_6876121602872584604[5] = 0;
   out_6876121602872584604[6] = 0;
   out_6876121602872584604[7] = 0;
   out_6876121602872584604[8] = 0;
   out_6876121602872584604[9] = 0;
   out_6876121602872584604[10] = 0;
   out_6876121602872584604[11] = 0;
   out_6876121602872584604[12] = 0;
   out_6876121602872584604[13] = 0;
   out_6876121602872584604[14] = 0;
   out_6876121602872584604[15] = 0;
   out_6876121602872584604[16] = 0;
   out_6876121602872584604[17] = 0;
   out_6876121602872584604[18] = 0;
   out_6876121602872584604[19] = 0;
   out_6876121602872584604[20] = 0;
   out_6876121602872584604[21] = 0;
   out_6876121602872584604[22] = 1;
   out_6876121602872584604[23] = 0;
   out_6876121602872584604[24] = 0;
   out_6876121602872584604[25] = 0;
   out_6876121602872584604[26] = 0;
   out_6876121602872584604[27] = 0;
   out_6876121602872584604[28] = 0;
   out_6876121602872584604[29] = 0;
   out_6876121602872584604[30] = 0;
   out_6876121602872584604[31] = 0;
   out_6876121602872584604[32] = 0;
   out_6876121602872584604[33] = 0;
   out_6876121602872584604[34] = 0;
   out_6876121602872584604[35] = 0;
   out_6876121602872584604[36] = 0;
   out_6876121602872584604[37] = 0;
   out_6876121602872584604[38] = 0;
   out_6876121602872584604[39] = 0;
   out_6876121602872584604[40] = 0;
   out_6876121602872584604[41] = 1;
   out_6876121602872584604[42] = 0;
   out_6876121602872584604[43] = 0;
   out_6876121602872584604[44] = 0;
   out_6876121602872584604[45] = 0;
   out_6876121602872584604[46] = 0;
   out_6876121602872584604[47] = 0;
   out_6876121602872584604[48] = 0;
   out_6876121602872584604[49] = 0;
   out_6876121602872584604[50] = 0;
   out_6876121602872584604[51] = 0;
   out_6876121602872584604[52] = 0;
   out_6876121602872584604[53] = 0;
}
void h_14(double *state, double *unused, double *out_5969212145833405866) {
   out_5969212145833405866[0] = state[6];
   out_5969212145833405866[1] = state[7];
   out_5969212145833405866[2] = state[8];
}
void H_14(double *state, double *unused, double *out_6125154571865432876) {
   out_6125154571865432876[0] = 0;
   out_6125154571865432876[1] = 0;
   out_6125154571865432876[2] = 0;
   out_6125154571865432876[3] = 0;
   out_6125154571865432876[4] = 0;
   out_6125154571865432876[5] = 0;
   out_6125154571865432876[6] = 1;
   out_6125154571865432876[7] = 0;
   out_6125154571865432876[8] = 0;
   out_6125154571865432876[9] = 0;
   out_6125154571865432876[10] = 0;
   out_6125154571865432876[11] = 0;
   out_6125154571865432876[12] = 0;
   out_6125154571865432876[13] = 0;
   out_6125154571865432876[14] = 0;
   out_6125154571865432876[15] = 0;
   out_6125154571865432876[16] = 0;
   out_6125154571865432876[17] = 0;
   out_6125154571865432876[18] = 0;
   out_6125154571865432876[19] = 0;
   out_6125154571865432876[20] = 0;
   out_6125154571865432876[21] = 0;
   out_6125154571865432876[22] = 0;
   out_6125154571865432876[23] = 0;
   out_6125154571865432876[24] = 0;
   out_6125154571865432876[25] = 1;
   out_6125154571865432876[26] = 0;
   out_6125154571865432876[27] = 0;
   out_6125154571865432876[28] = 0;
   out_6125154571865432876[29] = 0;
   out_6125154571865432876[30] = 0;
   out_6125154571865432876[31] = 0;
   out_6125154571865432876[32] = 0;
   out_6125154571865432876[33] = 0;
   out_6125154571865432876[34] = 0;
   out_6125154571865432876[35] = 0;
   out_6125154571865432876[36] = 0;
   out_6125154571865432876[37] = 0;
   out_6125154571865432876[38] = 0;
   out_6125154571865432876[39] = 0;
   out_6125154571865432876[40] = 0;
   out_6125154571865432876[41] = 0;
   out_6125154571865432876[42] = 0;
   out_6125154571865432876[43] = 0;
   out_6125154571865432876[44] = 1;
   out_6125154571865432876[45] = 0;
   out_6125154571865432876[46] = 0;
   out_6125154571865432876[47] = 0;
   out_6125154571865432876[48] = 0;
   out_6125154571865432876[49] = 0;
   out_6125154571865432876[50] = 0;
   out_6125154571865432876[51] = 0;
   out_6125154571865432876[52] = 0;
   out_6125154571865432876[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_8909220829729456592) {
  err_fun(nom_x, delta_x, out_8909220829729456592);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_8068156223905085053) {
  inv_err_fun(nom_x, true_x, out_8068156223905085053);
}
void pose_H_mod_fun(double *state, double *out_3205830260465553476) {
  H_mod_fun(state, out_3205830260465553476);
}
void pose_f_fun(double *state, double dt, double *out_4238396293587501899) {
  f_fun(state,  dt, out_4238396293587501899);
}
void pose_F_fun(double *state, double dt, double *out_6003141237729326165) {
  F_fun(state,  dt, out_6003141237729326165);
}
void pose_h_4(double *state, double *unused, double *out_6516003908446642780) {
  h_4(state, unused, out_6516003908446642780);
}
void pose_H_4(double *state, double *unused, double *out_8358348645504634211) {
  H_4(state, unused, out_8358348645504634211);
}
void pose_h_10(double *state, double *unused, double *out_5069419514865957544) {
  h_10(state, unused, out_5069419514865957544);
}
void pose_H_10(double *state, double *unused, double *out_2285557584559061390) {
  H_10(state, unused, out_2285557584559061390);
}
void pose_h_13(double *state, double *unused, double *out_3114619426317878324) {
  h_13(state, unused, out_3114619426317878324);
}
void pose_H_13(double *state, double *unused, double *out_6876121602872584604) {
  H_13(state, unused, out_6876121602872584604);
}
void pose_h_14(double *state, double *unused, double *out_5969212145833405866) {
  h_14(state, unused, out_5969212145833405866);
}
void pose_H_14(double *state, double *unused, double *out_6125154571865432876) {
  H_14(state, unused, out_6125154571865432876);
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

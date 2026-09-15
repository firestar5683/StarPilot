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
void err_fun(double *nom_x, double *delta_x, double *out_9222670015265418032) {
   out_9222670015265418032[0] = delta_x[0] + nom_x[0];
   out_9222670015265418032[1] = delta_x[1] + nom_x[1];
   out_9222670015265418032[2] = delta_x[2] + nom_x[2];
   out_9222670015265418032[3] = delta_x[3] + nom_x[3];
   out_9222670015265418032[4] = delta_x[4] + nom_x[4];
   out_9222670015265418032[5] = delta_x[5] + nom_x[5];
   out_9222670015265418032[6] = delta_x[6] + nom_x[6];
   out_9222670015265418032[7] = delta_x[7] + nom_x[7];
   out_9222670015265418032[8] = delta_x[8] + nom_x[8];
   out_9222670015265418032[9] = delta_x[9] + nom_x[9];
   out_9222670015265418032[10] = delta_x[10] + nom_x[10];
   out_9222670015265418032[11] = delta_x[11] + nom_x[11];
   out_9222670015265418032[12] = delta_x[12] + nom_x[12];
   out_9222670015265418032[13] = delta_x[13] + nom_x[13];
   out_9222670015265418032[14] = delta_x[14] + nom_x[14];
   out_9222670015265418032[15] = delta_x[15] + nom_x[15];
   out_9222670015265418032[16] = delta_x[16] + nom_x[16];
   out_9222670015265418032[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6734711869955682828) {
   out_6734711869955682828[0] = -nom_x[0] + true_x[0];
   out_6734711869955682828[1] = -nom_x[1] + true_x[1];
   out_6734711869955682828[2] = -nom_x[2] + true_x[2];
   out_6734711869955682828[3] = -nom_x[3] + true_x[3];
   out_6734711869955682828[4] = -nom_x[4] + true_x[4];
   out_6734711869955682828[5] = -nom_x[5] + true_x[5];
   out_6734711869955682828[6] = -nom_x[6] + true_x[6];
   out_6734711869955682828[7] = -nom_x[7] + true_x[7];
   out_6734711869955682828[8] = -nom_x[8] + true_x[8];
   out_6734711869955682828[9] = -nom_x[9] + true_x[9];
   out_6734711869955682828[10] = -nom_x[10] + true_x[10];
   out_6734711869955682828[11] = -nom_x[11] + true_x[11];
   out_6734711869955682828[12] = -nom_x[12] + true_x[12];
   out_6734711869955682828[13] = -nom_x[13] + true_x[13];
   out_6734711869955682828[14] = -nom_x[14] + true_x[14];
   out_6734711869955682828[15] = -nom_x[15] + true_x[15];
   out_6734711869955682828[16] = -nom_x[16] + true_x[16];
   out_6734711869955682828[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_3054834377026573453) {
   out_3054834377026573453[0] = 1.0;
   out_3054834377026573453[1] = 0.0;
   out_3054834377026573453[2] = 0.0;
   out_3054834377026573453[3] = 0.0;
   out_3054834377026573453[4] = 0.0;
   out_3054834377026573453[5] = 0.0;
   out_3054834377026573453[6] = 0.0;
   out_3054834377026573453[7] = 0.0;
   out_3054834377026573453[8] = 0.0;
   out_3054834377026573453[9] = 0.0;
   out_3054834377026573453[10] = 0.0;
   out_3054834377026573453[11] = 0.0;
   out_3054834377026573453[12] = 0.0;
   out_3054834377026573453[13] = 0.0;
   out_3054834377026573453[14] = 0.0;
   out_3054834377026573453[15] = 0.0;
   out_3054834377026573453[16] = 0.0;
   out_3054834377026573453[17] = 0.0;
   out_3054834377026573453[18] = 0.0;
   out_3054834377026573453[19] = 1.0;
   out_3054834377026573453[20] = 0.0;
   out_3054834377026573453[21] = 0.0;
   out_3054834377026573453[22] = 0.0;
   out_3054834377026573453[23] = 0.0;
   out_3054834377026573453[24] = 0.0;
   out_3054834377026573453[25] = 0.0;
   out_3054834377026573453[26] = 0.0;
   out_3054834377026573453[27] = 0.0;
   out_3054834377026573453[28] = 0.0;
   out_3054834377026573453[29] = 0.0;
   out_3054834377026573453[30] = 0.0;
   out_3054834377026573453[31] = 0.0;
   out_3054834377026573453[32] = 0.0;
   out_3054834377026573453[33] = 0.0;
   out_3054834377026573453[34] = 0.0;
   out_3054834377026573453[35] = 0.0;
   out_3054834377026573453[36] = 0.0;
   out_3054834377026573453[37] = 0.0;
   out_3054834377026573453[38] = 1.0;
   out_3054834377026573453[39] = 0.0;
   out_3054834377026573453[40] = 0.0;
   out_3054834377026573453[41] = 0.0;
   out_3054834377026573453[42] = 0.0;
   out_3054834377026573453[43] = 0.0;
   out_3054834377026573453[44] = 0.0;
   out_3054834377026573453[45] = 0.0;
   out_3054834377026573453[46] = 0.0;
   out_3054834377026573453[47] = 0.0;
   out_3054834377026573453[48] = 0.0;
   out_3054834377026573453[49] = 0.0;
   out_3054834377026573453[50] = 0.0;
   out_3054834377026573453[51] = 0.0;
   out_3054834377026573453[52] = 0.0;
   out_3054834377026573453[53] = 0.0;
   out_3054834377026573453[54] = 0.0;
   out_3054834377026573453[55] = 0.0;
   out_3054834377026573453[56] = 0.0;
   out_3054834377026573453[57] = 1.0;
   out_3054834377026573453[58] = 0.0;
   out_3054834377026573453[59] = 0.0;
   out_3054834377026573453[60] = 0.0;
   out_3054834377026573453[61] = 0.0;
   out_3054834377026573453[62] = 0.0;
   out_3054834377026573453[63] = 0.0;
   out_3054834377026573453[64] = 0.0;
   out_3054834377026573453[65] = 0.0;
   out_3054834377026573453[66] = 0.0;
   out_3054834377026573453[67] = 0.0;
   out_3054834377026573453[68] = 0.0;
   out_3054834377026573453[69] = 0.0;
   out_3054834377026573453[70] = 0.0;
   out_3054834377026573453[71] = 0.0;
   out_3054834377026573453[72] = 0.0;
   out_3054834377026573453[73] = 0.0;
   out_3054834377026573453[74] = 0.0;
   out_3054834377026573453[75] = 0.0;
   out_3054834377026573453[76] = 1.0;
   out_3054834377026573453[77] = 0.0;
   out_3054834377026573453[78] = 0.0;
   out_3054834377026573453[79] = 0.0;
   out_3054834377026573453[80] = 0.0;
   out_3054834377026573453[81] = 0.0;
   out_3054834377026573453[82] = 0.0;
   out_3054834377026573453[83] = 0.0;
   out_3054834377026573453[84] = 0.0;
   out_3054834377026573453[85] = 0.0;
   out_3054834377026573453[86] = 0.0;
   out_3054834377026573453[87] = 0.0;
   out_3054834377026573453[88] = 0.0;
   out_3054834377026573453[89] = 0.0;
   out_3054834377026573453[90] = 0.0;
   out_3054834377026573453[91] = 0.0;
   out_3054834377026573453[92] = 0.0;
   out_3054834377026573453[93] = 0.0;
   out_3054834377026573453[94] = 0.0;
   out_3054834377026573453[95] = 1.0;
   out_3054834377026573453[96] = 0.0;
   out_3054834377026573453[97] = 0.0;
   out_3054834377026573453[98] = 0.0;
   out_3054834377026573453[99] = 0.0;
   out_3054834377026573453[100] = 0.0;
   out_3054834377026573453[101] = 0.0;
   out_3054834377026573453[102] = 0.0;
   out_3054834377026573453[103] = 0.0;
   out_3054834377026573453[104] = 0.0;
   out_3054834377026573453[105] = 0.0;
   out_3054834377026573453[106] = 0.0;
   out_3054834377026573453[107] = 0.0;
   out_3054834377026573453[108] = 0.0;
   out_3054834377026573453[109] = 0.0;
   out_3054834377026573453[110] = 0.0;
   out_3054834377026573453[111] = 0.0;
   out_3054834377026573453[112] = 0.0;
   out_3054834377026573453[113] = 0.0;
   out_3054834377026573453[114] = 1.0;
   out_3054834377026573453[115] = 0.0;
   out_3054834377026573453[116] = 0.0;
   out_3054834377026573453[117] = 0.0;
   out_3054834377026573453[118] = 0.0;
   out_3054834377026573453[119] = 0.0;
   out_3054834377026573453[120] = 0.0;
   out_3054834377026573453[121] = 0.0;
   out_3054834377026573453[122] = 0.0;
   out_3054834377026573453[123] = 0.0;
   out_3054834377026573453[124] = 0.0;
   out_3054834377026573453[125] = 0.0;
   out_3054834377026573453[126] = 0.0;
   out_3054834377026573453[127] = 0.0;
   out_3054834377026573453[128] = 0.0;
   out_3054834377026573453[129] = 0.0;
   out_3054834377026573453[130] = 0.0;
   out_3054834377026573453[131] = 0.0;
   out_3054834377026573453[132] = 0.0;
   out_3054834377026573453[133] = 1.0;
   out_3054834377026573453[134] = 0.0;
   out_3054834377026573453[135] = 0.0;
   out_3054834377026573453[136] = 0.0;
   out_3054834377026573453[137] = 0.0;
   out_3054834377026573453[138] = 0.0;
   out_3054834377026573453[139] = 0.0;
   out_3054834377026573453[140] = 0.0;
   out_3054834377026573453[141] = 0.0;
   out_3054834377026573453[142] = 0.0;
   out_3054834377026573453[143] = 0.0;
   out_3054834377026573453[144] = 0.0;
   out_3054834377026573453[145] = 0.0;
   out_3054834377026573453[146] = 0.0;
   out_3054834377026573453[147] = 0.0;
   out_3054834377026573453[148] = 0.0;
   out_3054834377026573453[149] = 0.0;
   out_3054834377026573453[150] = 0.0;
   out_3054834377026573453[151] = 0.0;
   out_3054834377026573453[152] = 1.0;
   out_3054834377026573453[153] = 0.0;
   out_3054834377026573453[154] = 0.0;
   out_3054834377026573453[155] = 0.0;
   out_3054834377026573453[156] = 0.0;
   out_3054834377026573453[157] = 0.0;
   out_3054834377026573453[158] = 0.0;
   out_3054834377026573453[159] = 0.0;
   out_3054834377026573453[160] = 0.0;
   out_3054834377026573453[161] = 0.0;
   out_3054834377026573453[162] = 0.0;
   out_3054834377026573453[163] = 0.0;
   out_3054834377026573453[164] = 0.0;
   out_3054834377026573453[165] = 0.0;
   out_3054834377026573453[166] = 0.0;
   out_3054834377026573453[167] = 0.0;
   out_3054834377026573453[168] = 0.0;
   out_3054834377026573453[169] = 0.0;
   out_3054834377026573453[170] = 0.0;
   out_3054834377026573453[171] = 1.0;
   out_3054834377026573453[172] = 0.0;
   out_3054834377026573453[173] = 0.0;
   out_3054834377026573453[174] = 0.0;
   out_3054834377026573453[175] = 0.0;
   out_3054834377026573453[176] = 0.0;
   out_3054834377026573453[177] = 0.0;
   out_3054834377026573453[178] = 0.0;
   out_3054834377026573453[179] = 0.0;
   out_3054834377026573453[180] = 0.0;
   out_3054834377026573453[181] = 0.0;
   out_3054834377026573453[182] = 0.0;
   out_3054834377026573453[183] = 0.0;
   out_3054834377026573453[184] = 0.0;
   out_3054834377026573453[185] = 0.0;
   out_3054834377026573453[186] = 0.0;
   out_3054834377026573453[187] = 0.0;
   out_3054834377026573453[188] = 0.0;
   out_3054834377026573453[189] = 0.0;
   out_3054834377026573453[190] = 1.0;
   out_3054834377026573453[191] = 0.0;
   out_3054834377026573453[192] = 0.0;
   out_3054834377026573453[193] = 0.0;
   out_3054834377026573453[194] = 0.0;
   out_3054834377026573453[195] = 0.0;
   out_3054834377026573453[196] = 0.0;
   out_3054834377026573453[197] = 0.0;
   out_3054834377026573453[198] = 0.0;
   out_3054834377026573453[199] = 0.0;
   out_3054834377026573453[200] = 0.0;
   out_3054834377026573453[201] = 0.0;
   out_3054834377026573453[202] = 0.0;
   out_3054834377026573453[203] = 0.0;
   out_3054834377026573453[204] = 0.0;
   out_3054834377026573453[205] = 0.0;
   out_3054834377026573453[206] = 0.0;
   out_3054834377026573453[207] = 0.0;
   out_3054834377026573453[208] = 0.0;
   out_3054834377026573453[209] = 1.0;
   out_3054834377026573453[210] = 0.0;
   out_3054834377026573453[211] = 0.0;
   out_3054834377026573453[212] = 0.0;
   out_3054834377026573453[213] = 0.0;
   out_3054834377026573453[214] = 0.0;
   out_3054834377026573453[215] = 0.0;
   out_3054834377026573453[216] = 0.0;
   out_3054834377026573453[217] = 0.0;
   out_3054834377026573453[218] = 0.0;
   out_3054834377026573453[219] = 0.0;
   out_3054834377026573453[220] = 0.0;
   out_3054834377026573453[221] = 0.0;
   out_3054834377026573453[222] = 0.0;
   out_3054834377026573453[223] = 0.0;
   out_3054834377026573453[224] = 0.0;
   out_3054834377026573453[225] = 0.0;
   out_3054834377026573453[226] = 0.0;
   out_3054834377026573453[227] = 0.0;
   out_3054834377026573453[228] = 1.0;
   out_3054834377026573453[229] = 0.0;
   out_3054834377026573453[230] = 0.0;
   out_3054834377026573453[231] = 0.0;
   out_3054834377026573453[232] = 0.0;
   out_3054834377026573453[233] = 0.0;
   out_3054834377026573453[234] = 0.0;
   out_3054834377026573453[235] = 0.0;
   out_3054834377026573453[236] = 0.0;
   out_3054834377026573453[237] = 0.0;
   out_3054834377026573453[238] = 0.0;
   out_3054834377026573453[239] = 0.0;
   out_3054834377026573453[240] = 0.0;
   out_3054834377026573453[241] = 0.0;
   out_3054834377026573453[242] = 0.0;
   out_3054834377026573453[243] = 0.0;
   out_3054834377026573453[244] = 0.0;
   out_3054834377026573453[245] = 0.0;
   out_3054834377026573453[246] = 0.0;
   out_3054834377026573453[247] = 1.0;
   out_3054834377026573453[248] = 0.0;
   out_3054834377026573453[249] = 0.0;
   out_3054834377026573453[250] = 0.0;
   out_3054834377026573453[251] = 0.0;
   out_3054834377026573453[252] = 0.0;
   out_3054834377026573453[253] = 0.0;
   out_3054834377026573453[254] = 0.0;
   out_3054834377026573453[255] = 0.0;
   out_3054834377026573453[256] = 0.0;
   out_3054834377026573453[257] = 0.0;
   out_3054834377026573453[258] = 0.0;
   out_3054834377026573453[259] = 0.0;
   out_3054834377026573453[260] = 0.0;
   out_3054834377026573453[261] = 0.0;
   out_3054834377026573453[262] = 0.0;
   out_3054834377026573453[263] = 0.0;
   out_3054834377026573453[264] = 0.0;
   out_3054834377026573453[265] = 0.0;
   out_3054834377026573453[266] = 1.0;
   out_3054834377026573453[267] = 0.0;
   out_3054834377026573453[268] = 0.0;
   out_3054834377026573453[269] = 0.0;
   out_3054834377026573453[270] = 0.0;
   out_3054834377026573453[271] = 0.0;
   out_3054834377026573453[272] = 0.0;
   out_3054834377026573453[273] = 0.0;
   out_3054834377026573453[274] = 0.0;
   out_3054834377026573453[275] = 0.0;
   out_3054834377026573453[276] = 0.0;
   out_3054834377026573453[277] = 0.0;
   out_3054834377026573453[278] = 0.0;
   out_3054834377026573453[279] = 0.0;
   out_3054834377026573453[280] = 0.0;
   out_3054834377026573453[281] = 0.0;
   out_3054834377026573453[282] = 0.0;
   out_3054834377026573453[283] = 0.0;
   out_3054834377026573453[284] = 0.0;
   out_3054834377026573453[285] = 1.0;
   out_3054834377026573453[286] = 0.0;
   out_3054834377026573453[287] = 0.0;
   out_3054834377026573453[288] = 0.0;
   out_3054834377026573453[289] = 0.0;
   out_3054834377026573453[290] = 0.0;
   out_3054834377026573453[291] = 0.0;
   out_3054834377026573453[292] = 0.0;
   out_3054834377026573453[293] = 0.0;
   out_3054834377026573453[294] = 0.0;
   out_3054834377026573453[295] = 0.0;
   out_3054834377026573453[296] = 0.0;
   out_3054834377026573453[297] = 0.0;
   out_3054834377026573453[298] = 0.0;
   out_3054834377026573453[299] = 0.0;
   out_3054834377026573453[300] = 0.0;
   out_3054834377026573453[301] = 0.0;
   out_3054834377026573453[302] = 0.0;
   out_3054834377026573453[303] = 0.0;
   out_3054834377026573453[304] = 1.0;
   out_3054834377026573453[305] = 0.0;
   out_3054834377026573453[306] = 0.0;
   out_3054834377026573453[307] = 0.0;
   out_3054834377026573453[308] = 0.0;
   out_3054834377026573453[309] = 0.0;
   out_3054834377026573453[310] = 0.0;
   out_3054834377026573453[311] = 0.0;
   out_3054834377026573453[312] = 0.0;
   out_3054834377026573453[313] = 0.0;
   out_3054834377026573453[314] = 0.0;
   out_3054834377026573453[315] = 0.0;
   out_3054834377026573453[316] = 0.0;
   out_3054834377026573453[317] = 0.0;
   out_3054834377026573453[318] = 0.0;
   out_3054834377026573453[319] = 0.0;
   out_3054834377026573453[320] = 0.0;
   out_3054834377026573453[321] = 0.0;
   out_3054834377026573453[322] = 0.0;
   out_3054834377026573453[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_6521868085604382140) {
   out_6521868085604382140[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_6521868085604382140[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_6521868085604382140[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_6521868085604382140[3] = dt*state[12] + state[3];
   out_6521868085604382140[4] = dt*state[13] + state[4];
   out_6521868085604382140[5] = dt*state[14] + state[5];
   out_6521868085604382140[6] = state[6];
   out_6521868085604382140[7] = state[7];
   out_6521868085604382140[8] = state[8];
   out_6521868085604382140[9] = state[9];
   out_6521868085604382140[10] = state[10];
   out_6521868085604382140[11] = state[11];
   out_6521868085604382140[12] = state[12];
   out_6521868085604382140[13] = state[13];
   out_6521868085604382140[14] = state[14];
   out_6521868085604382140[15] = state[15];
   out_6521868085604382140[16] = state[16];
   out_6521868085604382140[17] = state[17];
}
void F_fun(double *state, double dt, double *out_7891921077140001268) {
   out_7891921077140001268[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7891921077140001268[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7891921077140001268[2] = 0;
   out_7891921077140001268[3] = 0;
   out_7891921077140001268[4] = 0;
   out_7891921077140001268[5] = 0;
   out_7891921077140001268[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7891921077140001268[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7891921077140001268[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7891921077140001268[9] = 0;
   out_7891921077140001268[10] = 0;
   out_7891921077140001268[11] = 0;
   out_7891921077140001268[12] = 0;
   out_7891921077140001268[13] = 0;
   out_7891921077140001268[14] = 0;
   out_7891921077140001268[15] = 0;
   out_7891921077140001268[16] = 0;
   out_7891921077140001268[17] = 0;
   out_7891921077140001268[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7891921077140001268[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7891921077140001268[20] = 0;
   out_7891921077140001268[21] = 0;
   out_7891921077140001268[22] = 0;
   out_7891921077140001268[23] = 0;
   out_7891921077140001268[24] = 0;
   out_7891921077140001268[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7891921077140001268[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7891921077140001268[27] = 0;
   out_7891921077140001268[28] = 0;
   out_7891921077140001268[29] = 0;
   out_7891921077140001268[30] = 0;
   out_7891921077140001268[31] = 0;
   out_7891921077140001268[32] = 0;
   out_7891921077140001268[33] = 0;
   out_7891921077140001268[34] = 0;
   out_7891921077140001268[35] = 0;
   out_7891921077140001268[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7891921077140001268[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7891921077140001268[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7891921077140001268[39] = 0;
   out_7891921077140001268[40] = 0;
   out_7891921077140001268[41] = 0;
   out_7891921077140001268[42] = 0;
   out_7891921077140001268[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7891921077140001268[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7891921077140001268[45] = 0;
   out_7891921077140001268[46] = 0;
   out_7891921077140001268[47] = 0;
   out_7891921077140001268[48] = 0;
   out_7891921077140001268[49] = 0;
   out_7891921077140001268[50] = 0;
   out_7891921077140001268[51] = 0;
   out_7891921077140001268[52] = 0;
   out_7891921077140001268[53] = 0;
   out_7891921077140001268[54] = 0;
   out_7891921077140001268[55] = 0;
   out_7891921077140001268[56] = 0;
   out_7891921077140001268[57] = 1;
   out_7891921077140001268[58] = 0;
   out_7891921077140001268[59] = 0;
   out_7891921077140001268[60] = 0;
   out_7891921077140001268[61] = 0;
   out_7891921077140001268[62] = 0;
   out_7891921077140001268[63] = 0;
   out_7891921077140001268[64] = 0;
   out_7891921077140001268[65] = 0;
   out_7891921077140001268[66] = dt;
   out_7891921077140001268[67] = 0;
   out_7891921077140001268[68] = 0;
   out_7891921077140001268[69] = 0;
   out_7891921077140001268[70] = 0;
   out_7891921077140001268[71] = 0;
   out_7891921077140001268[72] = 0;
   out_7891921077140001268[73] = 0;
   out_7891921077140001268[74] = 0;
   out_7891921077140001268[75] = 0;
   out_7891921077140001268[76] = 1;
   out_7891921077140001268[77] = 0;
   out_7891921077140001268[78] = 0;
   out_7891921077140001268[79] = 0;
   out_7891921077140001268[80] = 0;
   out_7891921077140001268[81] = 0;
   out_7891921077140001268[82] = 0;
   out_7891921077140001268[83] = 0;
   out_7891921077140001268[84] = 0;
   out_7891921077140001268[85] = dt;
   out_7891921077140001268[86] = 0;
   out_7891921077140001268[87] = 0;
   out_7891921077140001268[88] = 0;
   out_7891921077140001268[89] = 0;
   out_7891921077140001268[90] = 0;
   out_7891921077140001268[91] = 0;
   out_7891921077140001268[92] = 0;
   out_7891921077140001268[93] = 0;
   out_7891921077140001268[94] = 0;
   out_7891921077140001268[95] = 1;
   out_7891921077140001268[96] = 0;
   out_7891921077140001268[97] = 0;
   out_7891921077140001268[98] = 0;
   out_7891921077140001268[99] = 0;
   out_7891921077140001268[100] = 0;
   out_7891921077140001268[101] = 0;
   out_7891921077140001268[102] = 0;
   out_7891921077140001268[103] = 0;
   out_7891921077140001268[104] = dt;
   out_7891921077140001268[105] = 0;
   out_7891921077140001268[106] = 0;
   out_7891921077140001268[107] = 0;
   out_7891921077140001268[108] = 0;
   out_7891921077140001268[109] = 0;
   out_7891921077140001268[110] = 0;
   out_7891921077140001268[111] = 0;
   out_7891921077140001268[112] = 0;
   out_7891921077140001268[113] = 0;
   out_7891921077140001268[114] = 1;
   out_7891921077140001268[115] = 0;
   out_7891921077140001268[116] = 0;
   out_7891921077140001268[117] = 0;
   out_7891921077140001268[118] = 0;
   out_7891921077140001268[119] = 0;
   out_7891921077140001268[120] = 0;
   out_7891921077140001268[121] = 0;
   out_7891921077140001268[122] = 0;
   out_7891921077140001268[123] = 0;
   out_7891921077140001268[124] = 0;
   out_7891921077140001268[125] = 0;
   out_7891921077140001268[126] = 0;
   out_7891921077140001268[127] = 0;
   out_7891921077140001268[128] = 0;
   out_7891921077140001268[129] = 0;
   out_7891921077140001268[130] = 0;
   out_7891921077140001268[131] = 0;
   out_7891921077140001268[132] = 0;
   out_7891921077140001268[133] = 1;
   out_7891921077140001268[134] = 0;
   out_7891921077140001268[135] = 0;
   out_7891921077140001268[136] = 0;
   out_7891921077140001268[137] = 0;
   out_7891921077140001268[138] = 0;
   out_7891921077140001268[139] = 0;
   out_7891921077140001268[140] = 0;
   out_7891921077140001268[141] = 0;
   out_7891921077140001268[142] = 0;
   out_7891921077140001268[143] = 0;
   out_7891921077140001268[144] = 0;
   out_7891921077140001268[145] = 0;
   out_7891921077140001268[146] = 0;
   out_7891921077140001268[147] = 0;
   out_7891921077140001268[148] = 0;
   out_7891921077140001268[149] = 0;
   out_7891921077140001268[150] = 0;
   out_7891921077140001268[151] = 0;
   out_7891921077140001268[152] = 1;
   out_7891921077140001268[153] = 0;
   out_7891921077140001268[154] = 0;
   out_7891921077140001268[155] = 0;
   out_7891921077140001268[156] = 0;
   out_7891921077140001268[157] = 0;
   out_7891921077140001268[158] = 0;
   out_7891921077140001268[159] = 0;
   out_7891921077140001268[160] = 0;
   out_7891921077140001268[161] = 0;
   out_7891921077140001268[162] = 0;
   out_7891921077140001268[163] = 0;
   out_7891921077140001268[164] = 0;
   out_7891921077140001268[165] = 0;
   out_7891921077140001268[166] = 0;
   out_7891921077140001268[167] = 0;
   out_7891921077140001268[168] = 0;
   out_7891921077140001268[169] = 0;
   out_7891921077140001268[170] = 0;
   out_7891921077140001268[171] = 1;
   out_7891921077140001268[172] = 0;
   out_7891921077140001268[173] = 0;
   out_7891921077140001268[174] = 0;
   out_7891921077140001268[175] = 0;
   out_7891921077140001268[176] = 0;
   out_7891921077140001268[177] = 0;
   out_7891921077140001268[178] = 0;
   out_7891921077140001268[179] = 0;
   out_7891921077140001268[180] = 0;
   out_7891921077140001268[181] = 0;
   out_7891921077140001268[182] = 0;
   out_7891921077140001268[183] = 0;
   out_7891921077140001268[184] = 0;
   out_7891921077140001268[185] = 0;
   out_7891921077140001268[186] = 0;
   out_7891921077140001268[187] = 0;
   out_7891921077140001268[188] = 0;
   out_7891921077140001268[189] = 0;
   out_7891921077140001268[190] = 1;
   out_7891921077140001268[191] = 0;
   out_7891921077140001268[192] = 0;
   out_7891921077140001268[193] = 0;
   out_7891921077140001268[194] = 0;
   out_7891921077140001268[195] = 0;
   out_7891921077140001268[196] = 0;
   out_7891921077140001268[197] = 0;
   out_7891921077140001268[198] = 0;
   out_7891921077140001268[199] = 0;
   out_7891921077140001268[200] = 0;
   out_7891921077140001268[201] = 0;
   out_7891921077140001268[202] = 0;
   out_7891921077140001268[203] = 0;
   out_7891921077140001268[204] = 0;
   out_7891921077140001268[205] = 0;
   out_7891921077140001268[206] = 0;
   out_7891921077140001268[207] = 0;
   out_7891921077140001268[208] = 0;
   out_7891921077140001268[209] = 1;
   out_7891921077140001268[210] = 0;
   out_7891921077140001268[211] = 0;
   out_7891921077140001268[212] = 0;
   out_7891921077140001268[213] = 0;
   out_7891921077140001268[214] = 0;
   out_7891921077140001268[215] = 0;
   out_7891921077140001268[216] = 0;
   out_7891921077140001268[217] = 0;
   out_7891921077140001268[218] = 0;
   out_7891921077140001268[219] = 0;
   out_7891921077140001268[220] = 0;
   out_7891921077140001268[221] = 0;
   out_7891921077140001268[222] = 0;
   out_7891921077140001268[223] = 0;
   out_7891921077140001268[224] = 0;
   out_7891921077140001268[225] = 0;
   out_7891921077140001268[226] = 0;
   out_7891921077140001268[227] = 0;
   out_7891921077140001268[228] = 1;
   out_7891921077140001268[229] = 0;
   out_7891921077140001268[230] = 0;
   out_7891921077140001268[231] = 0;
   out_7891921077140001268[232] = 0;
   out_7891921077140001268[233] = 0;
   out_7891921077140001268[234] = 0;
   out_7891921077140001268[235] = 0;
   out_7891921077140001268[236] = 0;
   out_7891921077140001268[237] = 0;
   out_7891921077140001268[238] = 0;
   out_7891921077140001268[239] = 0;
   out_7891921077140001268[240] = 0;
   out_7891921077140001268[241] = 0;
   out_7891921077140001268[242] = 0;
   out_7891921077140001268[243] = 0;
   out_7891921077140001268[244] = 0;
   out_7891921077140001268[245] = 0;
   out_7891921077140001268[246] = 0;
   out_7891921077140001268[247] = 1;
   out_7891921077140001268[248] = 0;
   out_7891921077140001268[249] = 0;
   out_7891921077140001268[250] = 0;
   out_7891921077140001268[251] = 0;
   out_7891921077140001268[252] = 0;
   out_7891921077140001268[253] = 0;
   out_7891921077140001268[254] = 0;
   out_7891921077140001268[255] = 0;
   out_7891921077140001268[256] = 0;
   out_7891921077140001268[257] = 0;
   out_7891921077140001268[258] = 0;
   out_7891921077140001268[259] = 0;
   out_7891921077140001268[260] = 0;
   out_7891921077140001268[261] = 0;
   out_7891921077140001268[262] = 0;
   out_7891921077140001268[263] = 0;
   out_7891921077140001268[264] = 0;
   out_7891921077140001268[265] = 0;
   out_7891921077140001268[266] = 1;
   out_7891921077140001268[267] = 0;
   out_7891921077140001268[268] = 0;
   out_7891921077140001268[269] = 0;
   out_7891921077140001268[270] = 0;
   out_7891921077140001268[271] = 0;
   out_7891921077140001268[272] = 0;
   out_7891921077140001268[273] = 0;
   out_7891921077140001268[274] = 0;
   out_7891921077140001268[275] = 0;
   out_7891921077140001268[276] = 0;
   out_7891921077140001268[277] = 0;
   out_7891921077140001268[278] = 0;
   out_7891921077140001268[279] = 0;
   out_7891921077140001268[280] = 0;
   out_7891921077140001268[281] = 0;
   out_7891921077140001268[282] = 0;
   out_7891921077140001268[283] = 0;
   out_7891921077140001268[284] = 0;
   out_7891921077140001268[285] = 1;
   out_7891921077140001268[286] = 0;
   out_7891921077140001268[287] = 0;
   out_7891921077140001268[288] = 0;
   out_7891921077140001268[289] = 0;
   out_7891921077140001268[290] = 0;
   out_7891921077140001268[291] = 0;
   out_7891921077140001268[292] = 0;
   out_7891921077140001268[293] = 0;
   out_7891921077140001268[294] = 0;
   out_7891921077140001268[295] = 0;
   out_7891921077140001268[296] = 0;
   out_7891921077140001268[297] = 0;
   out_7891921077140001268[298] = 0;
   out_7891921077140001268[299] = 0;
   out_7891921077140001268[300] = 0;
   out_7891921077140001268[301] = 0;
   out_7891921077140001268[302] = 0;
   out_7891921077140001268[303] = 0;
   out_7891921077140001268[304] = 1;
   out_7891921077140001268[305] = 0;
   out_7891921077140001268[306] = 0;
   out_7891921077140001268[307] = 0;
   out_7891921077140001268[308] = 0;
   out_7891921077140001268[309] = 0;
   out_7891921077140001268[310] = 0;
   out_7891921077140001268[311] = 0;
   out_7891921077140001268[312] = 0;
   out_7891921077140001268[313] = 0;
   out_7891921077140001268[314] = 0;
   out_7891921077140001268[315] = 0;
   out_7891921077140001268[316] = 0;
   out_7891921077140001268[317] = 0;
   out_7891921077140001268[318] = 0;
   out_7891921077140001268[319] = 0;
   out_7891921077140001268[320] = 0;
   out_7891921077140001268[321] = 0;
   out_7891921077140001268[322] = 0;
   out_7891921077140001268[323] = 1;
}
void h_4(double *state, double *unused, double *out_6238203153530464174) {
   out_6238203153530464174[0] = state[6] + state[9];
   out_6238203153530464174[1] = state[7] + state[10];
   out_6238203153530464174[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_8902916183778532174) {
   out_8902916183778532174[0] = 0;
   out_8902916183778532174[1] = 0;
   out_8902916183778532174[2] = 0;
   out_8902916183778532174[3] = 0;
   out_8902916183778532174[4] = 0;
   out_8902916183778532174[5] = 0;
   out_8902916183778532174[6] = 1;
   out_8902916183778532174[7] = 0;
   out_8902916183778532174[8] = 0;
   out_8902916183778532174[9] = 1;
   out_8902916183778532174[10] = 0;
   out_8902916183778532174[11] = 0;
   out_8902916183778532174[12] = 0;
   out_8902916183778532174[13] = 0;
   out_8902916183778532174[14] = 0;
   out_8902916183778532174[15] = 0;
   out_8902916183778532174[16] = 0;
   out_8902916183778532174[17] = 0;
   out_8902916183778532174[18] = 0;
   out_8902916183778532174[19] = 0;
   out_8902916183778532174[20] = 0;
   out_8902916183778532174[21] = 0;
   out_8902916183778532174[22] = 0;
   out_8902916183778532174[23] = 0;
   out_8902916183778532174[24] = 0;
   out_8902916183778532174[25] = 1;
   out_8902916183778532174[26] = 0;
   out_8902916183778532174[27] = 0;
   out_8902916183778532174[28] = 1;
   out_8902916183778532174[29] = 0;
   out_8902916183778532174[30] = 0;
   out_8902916183778532174[31] = 0;
   out_8902916183778532174[32] = 0;
   out_8902916183778532174[33] = 0;
   out_8902916183778532174[34] = 0;
   out_8902916183778532174[35] = 0;
   out_8902916183778532174[36] = 0;
   out_8902916183778532174[37] = 0;
   out_8902916183778532174[38] = 0;
   out_8902916183778532174[39] = 0;
   out_8902916183778532174[40] = 0;
   out_8902916183778532174[41] = 0;
   out_8902916183778532174[42] = 0;
   out_8902916183778532174[43] = 0;
   out_8902916183778532174[44] = 1;
   out_8902916183778532174[45] = 0;
   out_8902916183778532174[46] = 0;
   out_8902916183778532174[47] = 1;
   out_8902916183778532174[48] = 0;
   out_8902916183778532174[49] = 0;
   out_8902916183778532174[50] = 0;
   out_8902916183778532174[51] = 0;
   out_8902916183778532174[52] = 0;
   out_8902916183778532174[53] = 0;
}
void h_10(double *state, double *unused, double *out_479264188908505210) {
   out_479264188908505210[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_479264188908505210[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_479264188908505210[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_5035106138755480521) {
   out_5035106138755480521[0] = 0;
   out_5035106138755480521[1] = 9.8100000000000005*cos(state[1]);
   out_5035106138755480521[2] = 0;
   out_5035106138755480521[3] = 0;
   out_5035106138755480521[4] = -state[8];
   out_5035106138755480521[5] = state[7];
   out_5035106138755480521[6] = 0;
   out_5035106138755480521[7] = state[5];
   out_5035106138755480521[8] = -state[4];
   out_5035106138755480521[9] = 0;
   out_5035106138755480521[10] = 0;
   out_5035106138755480521[11] = 0;
   out_5035106138755480521[12] = 1;
   out_5035106138755480521[13] = 0;
   out_5035106138755480521[14] = 0;
   out_5035106138755480521[15] = 1;
   out_5035106138755480521[16] = 0;
   out_5035106138755480521[17] = 0;
   out_5035106138755480521[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_5035106138755480521[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_5035106138755480521[20] = 0;
   out_5035106138755480521[21] = state[8];
   out_5035106138755480521[22] = 0;
   out_5035106138755480521[23] = -state[6];
   out_5035106138755480521[24] = -state[5];
   out_5035106138755480521[25] = 0;
   out_5035106138755480521[26] = state[3];
   out_5035106138755480521[27] = 0;
   out_5035106138755480521[28] = 0;
   out_5035106138755480521[29] = 0;
   out_5035106138755480521[30] = 0;
   out_5035106138755480521[31] = 1;
   out_5035106138755480521[32] = 0;
   out_5035106138755480521[33] = 0;
   out_5035106138755480521[34] = 1;
   out_5035106138755480521[35] = 0;
   out_5035106138755480521[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_5035106138755480521[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_5035106138755480521[38] = 0;
   out_5035106138755480521[39] = -state[7];
   out_5035106138755480521[40] = state[6];
   out_5035106138755480521[41] = 0;
   out_5035106138755480521[42] = state[4];
   out_5035106138755480521[43] = -state[3];
   out_5035106138755480521[44] = 0;
   out_5035106138755480521[45] = 0;
   out_5035106138755480521[46] = 0;
   out_5035106138755480521[47] = 0;
   out_5035106138755480521[48] = 0;
   out_5035106138755480521[49] = 0;
   out_5035106138755480521[50] = 1;
   out_5035106138755480521[51] = 0;
   out_5035106138755480521[52] = 0;
   out_5035106138755480521[53] = 1;
}
void h_13(double *state, double *unused, double *out_2296929327731223213) {
   out_2296929327731223213[0] = state[3];
   out_2296929327731223213[1] = state[4];
   out_2296929327731223213[2] = state[5];
}
void H_13(double *state, double *unused, double *out_5690642358446199373) {
   out_5690642358446199373[0] = 0;
   out_5690642358446199373[1] = 0;
   out_5690642358446199373[2] = 0;
   out_5690642358446199373[3] = 1;
   out_5690642358446199373[4] = 0;
   out_5690642358446199373[5] = 0;
   out_5690642358446199373[6] = 0;
   out_5690642358446199373[7] = 0;
   out_5690642358446199373[8] = 0;
   out_5690642358446199373[9] = 0;
   out_5690642358446199373[10] = 0;
   out_5690642358446199373[11] = 0;
   out_5690642358446199373[12] = 0;
   out_5690642358446199373[13] = 0;
   out_5690642358446199373[14] = 0;
   out_5690642358446199373[15] = 0;
   out_5690642358446199373[16] = 0;
   out_5690642358446199373[17] = 0;
   out_5690642358446199373[18] = 0;
   out_5690642358446199373[19] = 0;
   out_5690642358446199373[20] = 0;
   out_5690642358446199373[21] = 0;
   out_5690642358446199373[22] = 1;
   out_5690642358446199373[23] = 0;
   out_5690642358446199373[24] = 0;
   out_5690642358446199373[25] = 0;
   out_5690642358446199373[26] = 0;
   out_5690642358446199373[27] = 0;
   out_5690642358446199373[28] = 0;
   out_5690642358446199373[29] = 0;
   out_5690642358446199373[30] = 0;
   out_5690642358446199373[31] = 0;
   out_5690642358446199373[32] = 0;
   out_5690642358446199373[33] = 0;
   out_5690642358446199373[34] = 0;
   out_5690642358446199373[35] = 0;
   out_5690642358446199373[36] = 0;
   out_5690642358446199373[37] = 0;
   out_5690642358446199373[38] = 0;
   out_5690642358446199373[39] = 0;
   out_5690642358446199373[40] = 0;
   out_5690642358446199373[41] = 1;
   out_5690642358446199373[42] = 0;
   out_5690642358446199373[43] = 0;
   out_5690642358446199373[44] = 0;
   out_5690642358446199373[45] = 0;
   out_5690642358446199373[46] = 0;
   out_5690642358446199373[47] = 0;
   out_5690642358446199373[48] = 0;
   out_5690642358446199373[49] = 0;
   out_5690642358446199373[50] = 0;
   out_5690642358446199373[51] = 0;
   out_5690642358446199373[52] = 0;
   out_5690642358446199373[53] = 0;
}
void h_14(double *state, double *unused, double *out_8770212541449767783) {
   out_8770212541449767783[0] = state[6];
   out_8770212541449767783[1] = state[7];
   out_8770212541449767783[2] = state[8];
}
void H_14(double *state, double *unused, double *out_4939675327439047645) {
   out_4939675327439047645[0] = 0;
   out_4939675327439047645[1] = 0;
   out_4939675327439047645[2] = 0;
   out_4939675327439047645[3] = 0;
   out_4939675327439047645[4] = 0;
   out_4939675327439047645[5] = 0;
   out_4939675327439047645[6] = 1;
   out_4939675327439047645[7] = 0;
   out_4939675327439047645[8] = 0;
   out_4939675327439047645[9] = 0;
   out_4939675327439047645[10] = 0;
   out_4939675327439047645[11] = 0;
   out_4939675327439047645[12] = 0;
   out_4939675327439047645[13] = 0;
   out_4939675327439047645[14] = 0;
   out_4939675327439047645[15] = 0;
   out_4939675327439047645[16] = 0;
   out_4939675327439047645[17] = 0;
   out_4939675327439047645[18] = 0;
   out_4939675327439047645[19] = 0;
   out_4939675327439047645[20] = 0;
   out_4939675327439047645[21] = 0;
   out_4939675327439047645[22] = 0;
   out_4939675327439047645[23] = 0;
   out_4939675327439047645[24] = 0;
   out_4939675327439047645[25] = 1;
   out_4939675327439047645[26] = 0;
   out_4939675327439047645[27] = 0;
   out_4939675327439047645[28] = 0;
   out_4939675327439047645[29] = 0;
   out_4939675327439047645[30] = 0;
   out_4939675327439047645[31] = 0;
   out_4939675327439047645[32] = 0;
   out_4939675327439047645[33] = 0;
   out_4939675327439047645[34] = 0;
   out_4939675327439047645[35] = 0;
   out_4939675327439047645[36] = 0;
   out_4939675327439047645[37] = 0;
   out_4939675327439047645[38] = 0;
   out_4939675327439047645[39] = 0;
   out_4939675327439047645[40] = 0;
   out_4939675327439047645[41] = 0;
   out_4939675327439047645[42] = 0;
   out_4939675327439047645[43] = 0;
   out_4939675327439047645[44] = 1;
   out_4939675327439047645[45] = 0;
   out_4939675327439047645[46] = 0;
   out_4939675327439047645[47] = 0;
   out_4939675327439047645[48] = 0;
   out_4939675327439047645[49] = 0;
   out_4939675327439047645[50] = 0;
   out_4939675327439047645[51] = 0;
   out_4939675327439047645[52] = 0;
   out_4939675327439047645[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_9222670015265418032) {
  err_fun(nom_x, delta_x, out_9222670015265418032);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6734711869955682828) {
  inv_err_fun(nom_x, true_x, out_6734711869955682828);
}
void pose_H_mod_fun(double *state, double *out_3054834377026573453) {
  H_mod_fun(state, out_3054834377026573453);
}
void pose_f_fun(double *state, double dt, double *out_6521868085604382140) {
  f_fun(state,  dt, out_6521868085604382140);
}
void pose_F_fun(double *state, double dt, double *out_7891921077140001268) {
  F_fun(state,  dt, out_7891921077140001268);
}
void pose_h_4(double *state, double *unused, double *out_6238203153530464174) {
  h_4(state, unused, out_6238203153530464174);
}
void pose_H_4(double *state, double *unused, double *out_8902916183778532174) {
  H_4(state, unused, out_8902916183778532174);
}
void pose_h_10(double *state, double *unused, double *out_479264188908505210) {
  h_10(state, unused, out_479264188908505210);
}
void pose_H_10(double *state, double *unused, double *out_5035106138755480521) {
  H_10(state, unused, out_5035106138755480521);
}
void pose_h_13(double *state, double *unused, double *out_2296929327731223213) {
  h_13(state, unused, out_2296929327731223213);
}
void pose_H_13(double *state, double *unused, double *out_5690642358446199373) {
  H_13(state, unused, out_5690642358446199373);
}
void pose_h_14(double *state, double *unused, double *out_8770212541449767783) {
  h_14(state, unused, out_8770212541449767783);
}
void pose_H_14(double *state, double *unused, double *out_4939675327439047645) {
  H_14(state, unused, out_4939675327439047645);
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
